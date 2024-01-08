import os
import requests
import structlog
import logging
from datetime import datetime, timedelta
from time import sleep
import argparse
import yaml

def configure_logging(log_level=logging.INFO, log_file=None):
    # Configure the standard logging module for controlling the log level
    logging.basicConfig(level=log_level)

    # Configure structlog for more structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # If log_file is provided, configure a FileHandler to write logs to the specified file
    if log_file:
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

def read_config(log, config_file_path='config.yaml'):
    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
            if not config:
                raise ValueError("Config file is empty or not in YAML format.")
            
            # Load information from environment variables
            config['API']['booking_url'] = os.environ.get('API_URL', config['API']['booking_url'])
            config['API']['login_url'] = os.environ.get('API_LOGIN_URL', config['API']['login_url'])
            
        return config
    except FileNotFoundError:
        log.error(f"Error: Config file '{config_file_path}' not found.")
    except yaml.YAMLError as e:
        log.error(f"Error parsing '{config_file_path}': {e}")
    except Exception as e:
        log.error(f"An unexpected error occurred while reading the configuration: {e}")

    return None

def get_session_id(api_url, log):
    payload = {
        'versione': '26',
        'tipo': 'web',
        'pass': os.environ.get('API_PASSWORD', ''),
        'mail': os.environ.get('API_EMAIL', ''),
    }

    response = send_request(api_url, payload, log)

    if isinstance(response, dict):
        session_info = response.get('parametri', {}).get('sessione', {})
        codice_sessione = session_info.get('codice_sessione', '')

        if codice_sessione != '':
            return codice_sessione

    log.error("Failed to obtain session ID from the login API.")
    return None


def send_request(api_url, payload, log):
    max_attempts = 3
    attempt_counter = 0
    retry_interval = 300  # Retry interval in seconds, starting with 5 minutes

    while attempt_counter < max_attempts:
        try:
            response = requests.post(api_url, data=payload, timeout=(5, 30))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error("Failed to connect to the API server. Please check your internet connection and try again.", exception=str(e))
        
        # Exponential backoff for retries
        sleep(retry_interval)
        retry_interval *= 2
        attempt_counter += 1

    log.error("Maximum retry attempts reached. Unable to complete the API request.")
    return None

def is_already_booked(response):
    return response and response.get('status') == 1

def is_successful_booking(response):
    return response and response.get('status') == 2

def get_schedule_id_for_7am(api_url, session_id, target_date, log):
    data = {
        'id_sede': '5194',
        'codice_sessione': session_id,
        'giorno': target_date,
    }

    response = send_request(api_url, data, log)

    if response:
        lista_risultati = response.get('parametri', {}).get('lista_risultati', [])
        if lista_risultati:
            for risultato in lista_risultati:
                giorni = risultato.get('giorni', [])
                if giorni:
                    for giorno in giorni:
                        if giorno.get('giorno') == target_date:
                            orari_giorno = giorno.get('orari_giorno', [])
                            for schedule in orari_giorno:
                                if schedule.get('orario_inizio') == '07:00':
                                    return schedule.get('id_orario_palinsesto')

    log.warning("No schedule found for 7 am on the specified date.")
    return None

def book_gym_lesson(api_url, session_id, schedule_date, schedule_id, log):
    data = {
        'id_sede': '5194',
        'codice_sessione': session_id,
        'id_orario_palinsesto': schedule_id,
        'data': schedule_date,
    }
    return send_request(api_url, data, log)

def logout(api_url, session_id, log):
    data = {
        'codice_sessione': session_id,
    }

    response = send_request(api_url, data, log)

    if response and response.get('status') == 2:
        log.info("Successfully logged out.")
    else:
        log.warning("Failed to log out.")

def main():
    parser = argparse.ArgumentParser(description="Automated Gym Booking Script")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration file (default: config.yaml)")
    args = parser.parse_args()

    # Read log configuration from environment variables or use defaults
    log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    log_file = os.environ.get('LOG_FILE')

    configure_logging(log_level=log_level, log_file=log_file)
    log = structlog.get_logger()

    config = read_config(log)

    if config is None:
        log.error(f"Unable to load configuration. Please check the configuration file '{args.config}' and try again.")
        return

    api_url = config['API']['booking_url']
    login_url = config['API']['login_url']
    logout_url = config['API']['logout_url']
    schedule_api_url = config['API']['schedule_url']

    # Get session ID from the login API
    session_id = get_session_id(login_url, log)
    if session_id is None:
        log.error("Failed to obtain the session ID. Exiting.")
        return

    today = datetime.now()
    book_date = today + timedelta(days=4)
    schedule_date = book_date.strftime('%Y-%m-%d')

    schedule_id = get_schedule_id_for_7am(schedule_api_url, session_id, schedule_date, log)

    if schedule_id is not None:
        log.info("Attempting to book a gym lesson", date=book_date, scheduled_time='07:00')
        log.debug("API Request Payload", payload={'id_sede': '5194', 'codice_sessione': session_id, 'id_orario_palinsesto': schedule_id, 'data': schedule_date})

        attempt_counter = 0
        max_attempts = 3  # You can adjust the number of retry attempts

        while attempt_counter < max_attempts:
            response = book_gym_lesson(api_url, session_id, schedule_date, schedule_id, log)

            if response is not None:
                log.debug("API Response Payload", payload=response)

                if is_already_booked(response):
                    log.warning("You are already booked for the selected time.")
                    break  # Exit the loop, no need to retry
                elif is_successful_booking(response):
                    log.info("Congratulations! You have successfully booked a gym lesson.")
                    break  # Exit the loop, booking successful

            log.error("Failed to book a gym lesson. Retrying in 5 minutes...", attempt=attempt_counter + 1)
            attempt_counter += 1
            sleep(300)  # Retry after 5 minutes
        else:
            log.error("Maximum retry attempts reached. Unable to book a gym lesson.")
        
        logout(logout_url, session_id, log)
    else:
        log.warning("No schedule found for 7 am on the specified date.")

if __name__ == "__main__":
    main()
