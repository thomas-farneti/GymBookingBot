import requests
import structlog
from datetime import datetime, timedelta
from time import sleep
import yaml

def configure_logging():
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

def read_config(log):
    try:
        with open('config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        return config
    except FileNotFoundError:
        log.error("Config file 'config.yaml' not found. Please ensure the file exists.")
        return None
    except yaml.YAMLError as e:
        log.error(f"Error parsing 'config.yaml': {e}")
        return None

def send_request(api_url, headers, data, log):
    try:
        response = requests.post(api_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("Failed to connect to the gym booking server. Please check your internet connection and try again.", exception=str(e))
        return None

def is_already_booked(response):
    return response and response.get('status') == 1

def is_successful_booking(response):
    return response and response.get('status') == 2

def get_schedule_id(day_of_week, config):
    schedule_ids = config.get('SCHEDULE_IDS', {})
    return schedule_ids.get(day_of_week.lower(), None)

def book_gym_lesson(api_url, headers, session_id, schedule_date, schedule_id, log):
    data = {
        'id_sede': '5194',
        'codice_sessione': session_id,
        'id_orario_palinsesto': schedule_id,
        'data': schedule_date,
    }
    return send_request(api_url, headers, data, log)

def main():
    configure_logging()
    log = structlog.get_logger()

    config = read_config(log)

    if config is None:
        log.error("Unable to load configuration. Please check the configuration file 'config.yaml' and try again.")
        return

    api_url = config['API']['url']
    headers = config['HEADERS']
    session_id = config['SESSION']['id']

    today = datetime.now()
    book_date = today + timedelta(days=4)
    schedule_date = book_date.strftime('%Y-%m-%d')

    day_of_week = book_date.strftime('%A').lower()
    schedule_id = get_schedule_id(day_of_week, config)

    if schedule_id is not None:
        log.info("Attempting to book a gym lesson", date=book_date, day_of_week=day_of_week.capitalize())
        log.debug("API Request Payload", payload={'id_sede': '5194', 'codice_sessione': session_id, 'id_orario_palinsesto': schedule_id, 'data': schedule_date})

        attempt_counter = 0
        max_attempts = 3  # You can adjust the number of retry attempts

        while attempt_counter < max_attempts:
            response = book_gym_lesson(api_url, headers, session_id, schedule_date, schedule_id, log)

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
    else:
        log.warning("No schedule_id found for the current day.")

if __name__ == "__main__":
    main()
