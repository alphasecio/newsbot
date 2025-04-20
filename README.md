# 📰 newsbot
This script automates the process of fetching [Google Alerts](https://www.google.com/alerts) emails using IMAP, extracting article links, summarizing their contents using [OpenAI](https://platform.openai.com/docs) and [Firecrawl](https://www.firecrawl.dev/referral?rid=C6M8MJ69), and resending the results as an HTML email via [Resend](https://resend.com/docs).


### ✨ Features

- Connects to an IMAP email account
- Fetches unread Google Alerts messages (configurable)
- Parses and extracts article titles and links using OpenAI
- Summarizes article content via Firecrawl + OpenAI
- Sends compiled summaries to a specified recipient using Resend


### 🚀 Deploying to Railway

1. Click the button below to deploy:

   [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?referralCode=alphasec)

2. Create a new project and connect to this repo using `Deploy from a GitHub repo` option.
3. Set the required environment variables in the `Variables` tab.
4. Set the `Cron Schedule` in the `Settings` tab and click Deploy.


### 🌐 Environment Variables

| Variable             | Required | Description                                                                 |
|----------------------|----------|-----------------------------------------------------------------------------|
| `IMAP_SERVER`        |    ✅    | IMAP server (default: `"imap.mailo.com"`)                                   |
| `IMAP_PORT`          |    ✅    | IMAP port (default: `993`)                                                  |
| `MAILBOX_USER`       |    ✅    | Mailbox user                                                                |
| `MAILBOX_PASS`       |    ✅    | Mailbox password                                                            |
| `MAILBOX_FOLDER`     |    ✅    | Mailbox folder (default: `INBOX`)                                           |
| `MATCH_CRITERIA`     |    ✅    | Match criteria (default: `(FROM "googlealerts-noreply@google.com" UNSEEN)`) |
| `OPENAI_API_KEY`     |    ✅    | OpenAI API key                                                              |
| `OPENAI_MODEL`       |          | OpenAI model (default: `gpt-4o-mini`)                                       |
| `FIRECRAWL_API_KEY`  |    ✅    | Firecrawl API key                                                           |
| `RESEND_API_KEY`     |    ✅    | Resend API key                                                              |
| `EMAIL_FROM`         |    ✅    | Sender email address                                                        |
| `EMAIL_TO`           |    ✅    | Recipient email address                                                     |
