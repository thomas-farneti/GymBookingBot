# Gym Booking Bot

## Overview

GymBookingBot is a Python script that automates the process of booking gym lessons using the Gym's Booking API. The script runs daily and schedules the booking four days in advance.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [License](#license)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/GymBookingBot.git
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Configure the script by editing the `config.py` file.
2. Run the script:

   ```bash
   python gym_booking_job.py
   ```

3. Check the logs for information on the booking process.

## Configuration

Edit the `config.yaml` file to set up your authentication token, API endpoints, and other necessary parameters.

```yaml
# config.yaml

API:
  url: https://app.shaggyowl.com/funzioniapp/v407/prenotazione_new

HEADERS:
  Accept: '*/*'
  Accept-Language: 'en-US,en;q=0.9,it;q=0.8'
  Connection: 'keep-alive'
  Cookie: 'paste your Auth token here'
  DNT: '1'
  Origin: 'https://app.shaggyowl.com'
  Referer: 'https://app.shaggyowl.com/accesso-cliente/index.html'
  Sec-Fetch-Dest: 'empty'
  Sec-Fetch-Mode: 'cors'
  Sec-Fetch-Site: 'same-origin'
  User-Agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  content-type: 'application/x-www-form-urlencoded; charset=utf-8'
  sec-ch-ua: '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
  sec-ch-ua-mobile: '?0'
  sec-ch-ua-platform: '"Windows"'

SESSION:
  id: 'Paste you session Id here'

RETRY:
  max_attempts: 3
  retry_interval: 300

SCHEDULE_IDS:
  monday: '4379230'
  tuesday: '4379231'
  wednesday: '4379232'
  thursday: '4379233'
  friday: '4379234'


# Add other configuration parameters as needed
```

## Dependencies

- Python 3.x

## License

This project is licensed under the [MIT License](LICENSE).
```

You can copy the entire content and paste it into your README.md file. Adjust the placeholders such as `[Your Gym's Name]` and `[Gym's Booking API]` with your specific gym information.# GymBookingBot
Quick gym booking bot in python
