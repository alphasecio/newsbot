import resend
import os, json, email, imaplib, ssl, socket, time, logging
from email.header import decode_header
from openai import OpenAI
from firecrawl import FirecrawlApp

# Set up logging to capture stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Ensures logs appear in stdout
)

# Environment variables
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.mailo.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
MAILBOX_USER = os.getenv("MAILBOX_USER")
MAILBOX_PASS = os.getenv("MAILBOX_PASS")
MAILBOX_FOLDER = os.getenv("MAILBOX_FOLDER", "INBOX")
MATCH_CRITERIA = os.getenv("MATCH_CRITERIA", '(FROM "googlealerts-noreply@google.com" UNSEEN)')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "Newsletter Summary")

# Global clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

def connect_to_mailbox():
    try:
        logging.info("Connecting to mailbox...")
        mailbox = imaplib.IMAP4_SSL(IMAP_SERVER, int(IMAP_PORT))
        mailbox.login(MAILBOX_USER, MAILBOX_PASS)
        mailbox.select(MAILBOX_FOLDER)
        return mailbox, None
    except imaplib.IMAP4.error as e:
        error_msg = f"IMAP error: {e}"
        logging.error(error_msg)
        return None, error_msg
    except ssl.SSLError as e:
        error_msg = f"SSL error: {e}"
        logging.error(error_msg)
        return None, error_msg
    except socket.gaierror as e:
        error_msg = f"Socket address error: {e}"
        logging.error(error_msg)
        return None, error_msg
    except socket.timeout as e:
        error_msg = f"Socket timeout: {e}"
        logging.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error connecting to mailbox: {e}"
        logging.error(error_msg)
        return None, error_msg

def fetch_mails(mailbox):
    try:
        logging.info("Mailbox connected successfully. Fetching emails...")
        status, messages = mailbox.search(None, MATCH_CRITERIA)
        email_ids = messages[0].split()
        
        mails = []
        for email_id in email_ids:
            status, msg_data = mailbox.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    # Extract email body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                    mails.append({"subject": subject, "body": body})
            
            mailbox.store(email_id, "+FLAGS", "\\Seen") # Mark email as read
        return mails
    except Exception as e:
        logging.error(f"Error while fetching emails: {e}")

# Rate limiting for Firecrawl API
request_times = []
def rate_limit_firecrawl():
    global request_times
    # Remove timestamps older than 60 seconds
    now = time.time()
    request_times = [t for t in request_times if now - t < 60]

    if len(request_times) >= 10:  # If 10 requests were made in the last 60 seconds
        oldest_request = min(request_times)
        wait_time = max(0, 60 - (now - oldest_request))  # Time until first request is older than 60s
        if wait_time > 0:
            logging.warning(f"Rate limit reached! Waiting {wait_time:.2f} seconds before next request...")
            time.sleep(wait_time)

    request_times.append(time.time())

def summarize_url(url):
    try:
        logging.info(f"Retrieving content from and summarizing URL: {url}")
        scrape_result = firecrawl_client.scrape_url(url, params={'formats': ['markdown', 'html']})
        
        if not scrape_result or not scrape_result.get("markdown"):
            logging.error(f"Error while retrieving content from URL: {url}. Empty or invalid response.")
            return None
        else:
            summary = openai_client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": "Summarize the article succinctly in a maximum of 100-150 words."},
                    {"role": "user", "content": scrape_result.get("markdown", "")}
                ]
            )
            return summary
    except Exception as e:
        logging.error(f"Error while summarizing URL: {e}")
        return f"Error retrieving or processing content: {str(e)}"

def send_email(email_body):
    resend.api_key = RESEND_API_KEY       
    logging.info("Sending email...")
    try:
        email = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": EMAIL_SUBJECT,
            "html": f"{email_body}"
        })
        return True
    except Exception as e:
        logging.error(f"Error while sending email: {e}")
        return False

def extract_articles_from_email(email_body):
    try:
        logging.info("Processing email...")
        response = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "Extract only article titles and their corresponding links from the email newsletter. Include all articles. Do not include profile links, subscription links, or any other unnecessary links."},
                {"role": "user", "content": alert['body']}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "articles_list",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "articles": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "link": {"type": "string"}
                                    },
                                    "required": ["title", "link"],
                                    "additionalProperties": False 
                                }
                            }
                        },
                        "required": ["articles"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )

        articles_data = json.loads(response.output_text)
        return articles_data.get("articles", [])
    except Exception as e:
        logging.error(f"Error extracting articles: {e}")
        return []

def main():
    mailbox, error = connect_to_mailbox()
    
    if error:
        logging.error(f"Failed to connect to mailbox: {error}")
        return
    
    if not mailbox:
        logging.error("Mailbox connection failed without specific error.")
        return

    try:
        mails = fetch_mails(mailbox)
        
        if not mails:
            logging.info("No new emails found.")
            return
        
        all_articles = []
        for i, alert in enumerate(mails):
            articles = extract_articles_from_email(alert['body'])
            all_articles.extend(articles)

        if all_articles:
            try:
                email_body_parts = []
                for article in all_articles:
                    try:
                        rate_limit_firecrawl()
                        summary = summarize_url(article['link'])
                        article_html = f"""
                            <strong>{article['title']}</strong>
                            <p>{summary.output_text}</p>
                            <hr>
                        """
                        email_body_parts.append(article_html)

                    except Exception as e:
                        logging.error(f"Error summarizing article '{article.get('title', 'Unknown')}': {str(e)}")
                        continue
            except Exception as e:
                logging.error(f"Error generating content summaries: {str(e)}")

            if email_body_parts:
                body = "\n".join(email_body_parts)
                send_email(body)
            else:
                logging.info("No summaries generated, skipping email.")
    
    finally:
        try:
            mailbox.logout()
            logging.info("Successfully logged out from mailbox.")
        except Exception as e:
            logging.error(f"Error during mailbox logout: {e}")

if __name__ == "__main__":
    main()
