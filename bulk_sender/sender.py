import os
import csv
import time
import requests
import random
import argparse
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple, Set
import sys
from datetime import datetime
import glob
import re

sys.tracebacklimit = 0

def load_environment():
    if not os.path.exists('.secrets.env'):
        print("❌ ERROR: Secrets file '.secrets.env' not found.")
        sys.exit(1)
    load_dotenv(dotenv_path='.secrets.env')
    required_vars = ['EVOLUTION_API_URL', 'EVOLUTION_API_KEY', 'EVOLUTION_INSTANCE_NAME']
    if missing_vars := [v for v in required_vars if not os.getenv(v)]:
        print(f"❌ ERROR: Missing environment variables in '.secrets.env': {', '.join(missing_vars)}")
        sys.exit(1)

def send_text_message(api_url: str, api_key: str, instance_name: str, number: str, message: str) -> Tuple[bool, str]:
    endpoint = f"{api_url}/message/sendText/{instance_name}"
    headers = {"apikey": api_key}
    payload = {"number": number, "options": {"delay": 1200, "presence": "composing"}, "text": message}
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
        if response.status_code in [200, 201]:
            return True, response.json().get('key', {}).get('id', 'N/A')
        return False, f"Status: {response.status_code}, Response: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection ERROR: {e}"

def send_media_message(api_url: str, api_key: str, instance_name: str, number: str, media_path: str) -> Tuple[bool, str]:
    endpoint = f"{api_url}/message/sendMedia/{instance_name}"
    headers = {"apikey": api_key}
    try:
        with open(media_path, 'rb') as f:
            files = {'file': (os.path.basename(media_path), f)}
            data = {'number': number, 'options[delay]': 1200, 'options[presence]': 'composing', 'mediatype': 'video'}
            response = requests.post(endpoint, headers=headers, data=data, files=files, timeout=30)
        if response.status_code in [200, 201]:
            return True, response.json().get('key', {}).get('id', 'N/A')
        return False, f"Status: {response.status_code}, Response: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection ERROR: {e}"
    except FileNotFoundError:
        print(f"❌ FATAL: Video file not found at path: {media_path}")
        sys.exit(1)

def clean_phone_number(phone_string: str) -> Optional[str]:
    if not phone_string: return None
    potential_numbers = re.findall(r'\b\d{7,10}\b', phone_string)
    for number in potential_numbers:
        if len(number) == 10:
            return f"57{number}"
    return None

def read_message_template(file_path: str) -> str:
    if not os.path.exists(file_path):
        print(f"❌ FATAL: Message file not found at '{file_path}'")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def get_latest_report(directory: str) -> Optional[str]:
    report_files = glob.glob(os.path.join(directory, "sending_report_*.csv"))
    if not report_files: return None
    return max(report_files, key=os.path.getmtime)

def load_processed_contacts(report_path: Optional[str]) -> Set[str]:
    if not report_path or not os.path.exists(report_path):
        return set()

    processed = set()
    with open(report_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone_number = row.get('phone_number')
            if not phone_number:
                continue

            if row.get('message_type') == 'VIDEO' and row.get('status') == 'SUCCESS':
                processed.add(phone_number)

            if row.get('message_type') == 'TEXT' and row.get('status') == 'FAILED':
                details = row.get('details', '')
                if '"exists":false' in details:
                    processed.add(phone_number)

    if processed:
        print(f"🔍 Found {len(processed)} contacts already processed or confirmed invalid in '{os.path.basename(report_path)}'. They will be skipped.")
    return processed

def setup_report_writer(directory: str, resume_path: Optional[str]) -> Tuple[Any, Any, str]:
    if resume_path:
        print(f"📄 Resuming session. Appending to report: '{os.path.basename(resume_path)}'")
        file = open(resume_path, 'a', newline='', encoding='utf-8')
        writer = csv.writer(file)
        return file, writer, resume_path
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = f"sending_report_{timestamp}.csv"
        report_path = os.path.join(directory, report_filename)
        file = open(report_path, 'w', newline='', encoding='utf-8')
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'phone_number', 'contact_name', 'message_type', 'status', 'details'])
        print(f"📄 New session. Report will be generated at: {report_path}")
        return file, writer, report_path

def log_to_report(writer, phone, name, msg_type, status, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([timestamp, phone, name, msg_type, status, details])

def main():
    parser = argparse.ArgumentParser(description="Deduplicating and Resumable WhatsApp bulk sender.")
    parser.add_argument("csv_file", help="Path to the .csv file with contacts.")
    parser.add_argument("message_file", help="Path to the .txt file with the message. Use {name} as placeholder.")
    parser.add_argument("video_file", help="Path to the video file to be sent.")
    args = parser.parse_args()

    load_environment()
    api_url, api_key, instance_name = os.getenv('EVOLUTION_API_URL'), os.getenv('EVOLUTION_API_KEY'), os.getenv('EVOLUTION_INSTANCE_NAME')

    delay_text_video_min = float(os.getenv('TEXT_TO_VIDEO_DELAY_MIN', 4))
    delay_text_video_max = float(os.getenv('TEXT_TO_VIDEO_DELAY_MAX', 7))
    delay_inter_contact_min = float(os.getenv('INTER_CONTACT_DELAY_MIN', 15))
    delay_inter_contact_max = float(os.getenv('INTER_CONTACT_DELAY_MAX', 30))

    print("--- STARTING DEDUPLICATING BULK SENDING PROCESS ---")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    latest_report = get_latest_report(script_dir)

    processed_contacts = load_processed_contacts(latest_report)

    session_sent_contacts = set()

    report_file, report_writer, report_path = setup_report_writer(script_dir, latest_report)

    message_template = read_message_template(args.message_file)

    contacts_to_process = []
    skipped_validation_count = 0
    skipped_duplicate_count = 0

    try:
        with open(args.csv_file, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Nombre Propietario", "").strip()
                phone_str = row.get("Telefono Propietario", "")
                clean_number = clean_phone_number(phone_str)

                if not name or not clean_number:
                    reason = "Missing name" if not name else "No valid phone number found"
                    log_to_report(report_writer, phone_str, name, 'VALIDATION', 'SKIPPED', reason)
                    skipped_validation_count += 1
                    continue

                if clean_number in processed_contacts or clean_number in session_sent_contacts:
                    if clean_number not in processed_contacts:
                        skipped_duplicate_count += 1
                    continue

                contacts_to_process.append({"name": name, "phone": clean_number})
                session_sent_contacts.add(clean_number)

        if skipped_validation_count > 0:
            print(f"⏭️  Skipped {skipped_validation_count} rows due to invalid data (see report for details).")
        if skipped_duplicate_count > 0:
            print(f"⏭️  Skipped {skipped_duplicate_count} duplicate contacts found within the CSV file.")

        if not contacts_to_process:
            print("✅ All contacts have already been processed or were invalid/duplicates. Nothing to do.")
            return

        total = len(contacts_to_process)
        print(f"✅ Found {total} unique contacts remaining to process.")
        sent_count, failed_count = 0, 0

        for i, contact in enumerate(contacts_to_process):
            print(f"\n--- Processing {i+1}/{total} for {contact['name']} ({contact['phone']}) ---")

            first_name = contact['name'].split()[0]
            personalized_message = message_template.replace("{nombre}", first_name)

            text_sent, text_details = send_text_message(api_url, api_key, instance_name, contact['phone'], personalized_message)
            log_to_report(report_writer, contact['phone'], contact['name'], 'TEXT', 'SUCCESS' if text_sent else 'FAILED', text_details)

            if text_sent:
                text_video_delay = random.uniform(delay_text_video_min, delay_text_video_max)
                print(f"  ⏱️  Waiting {text_video_delay:.2f}s before sending video...")
                time.sleep(text_video_delay)

                video_sent, video_details = send_media_message(api_url, api_key, instance_name, contact['phone'], args.video_file)
                log_to_report(report_writer, contact['phone'], contact['name'], 'VIDEO', 'SUCCESS' if video_sent else 'FAILED', video_details)

                if video_sent:
                    sent_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

            if i < total - 1:
                inter_contact_delay = random.uniform(delay_inter_contact_min, delay_inter_contact_max)
                print(f"⏱️  Waiting {inter_contact_delay:.2f}s for the next contact...")
                time.sleep(inter_contact_delay)
    finally:
        report_file.close()
        print(f"\n📄 Report updated: {report_path}")

    print("\n--- PROCESS FINISHED ---")
    print(f"✔️ Sequences completed in this session: {sent_count}")
    print(f"❌ Failed sequences in this session: {failed_count}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🚫 Process interrupted by user. Aborting.")
        sys.exit(0)