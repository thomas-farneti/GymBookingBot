import requests
import structlog
import logging
from datetime import datetime, timedelta
from time import sleep
import argparse

def configure_logging(log_level=logging.INFO, log_file=None):
    # Configure the standard logging module for controlling the log level
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    # If log_file is provided, configure a FileHandler to write logs to the specified file
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a')  # Use 'a' for append mode
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

def get_session_id(log, email, psw):
    payload = {
        'versione': '26',
        'tipo': 'web',
        'pass': psw,
        'mail': email
    }

    response = send_request('https://app.shaggyowl.com/funzioniapp/v407/loginApp', payload, log)

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

    headers =  {'content-type':'application/x-www-form-urlencoded; charset=utf-8'}

    while attempt_counter < max_attempts:
        try:
            response = requests.post(api_url, data=payload,headers=headers, timeout=(5, 30))
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

def get_schedule_id_for_7am(session_id, target_date, log):
    data = {
        'id_sede': '5194',
        'codice_sessione': session_id,
        'giorno': target_date,
    }

    response = send_request('https://app.shaggyowl.com/funzioniapp/v407/palinsesti', data, log)

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

def book_gym_lesson(session_id, schedule_date, schedule_id, log):
    data = {
        'id_sede': '5194',
        'codice_sessione': session_id,
        'id_orario_palinsesto': schedule_id,
        'data': schedule_date,
    }
    return send_request('https://app.shaggyowl.com/funzioniapp/v407/prenotazione_new', data, log)

def logout(session_id, log):
    data = {
        'codice_sessione': session_id,
    }

    response = send_request('https://app.shaggyowl.com/funzioniapp/v407/logout', data, log)

    if response and response.get('status') == 2:
        log.info("Successfully logged out.")
    else:
        log.warning("Failed to log out.")

def main():
    parser = argparse.ArgumentParser(description="Automated Gym Booking Script")
    parser.add_argument("--email", required=True, help="Your email for login")
    parser.add_argument("--password", required=True, help="Your password for login")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")
    parser.add_argument("--log-file", help="Path to the log file")

    args = parser.parse_args()

    # Read log configuration from command-line arguments
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    log_file = args.log_file

    configure_logging(log_level=log_level, log_file=log_file)
    log = logging.getLogger(__name__)

    email = args.email
    psw = args.password

    # Get session ID from the login API
    session_id = get_session_id(log, email=email, psw=psw)
    if session_id is None:
        log.error("Failed to obtain the session ID. Exiting.")
        return

    today = datetime.now()
    book_date = today + timedelta(days=4)
    schedule_date = book_date.strftime('%Y-%m-%d')

    schedule_id = get_schedule_id_for_7am(session_id, schedule_date, log)

    if schedule_id is not None:
        log.info("Attempting to book a gym lesson", date=book_date, scheduled_time='07:00')
        log.debug("API Request Payload", payload={'id_sede': '5194', 'codice_sessione': session_id, 'id_orario_palinsesto': schedule_id, 'data': schedule_date})

        response = book_gym_lesson(session_id, schedule_date, schedule_id, log)

        if response is not None:
            log.debug("API Response Payload", payload=response)

            if is_already_booked(response):
                log.warning("You are already booked for the selected time.")
            elif is_successful_booking(response):
                log.info("Congratulations! You have successfully booked a gym lesson.")

        log.error("Failed to book a gym lesson.")
        
        logout(session_id, log)
    else:
        log_message = 'No schedule found for 7 am on the specified date.'
        log.warning(log_message)

if __name__ == "__main__":
    main()
