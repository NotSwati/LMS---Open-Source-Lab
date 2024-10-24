import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

def send_email(user_email, book_title, issue_date, due_date):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587  # For TLS
    sender_email = 'preet.dhillon2142@gmail.com'  # Replace with your Gmail email
    sender_password = 'homj gzxy czlv uvdw'  # Replace with your generated App Password

    msg = EmailMessage()
    msg['Subject'] = f'Book Issued: {book_title}'
    msg['From'] = sender_email
    msg['To'] = user_email
    msg.set_content(f"""
    Dear User,

    You have successfully issued the book titled '{book_title}'.

    Issue Date: {issue_date.strftime('%Y-%m-%d')}
    Due Date: {due_date.strftime('%Y-%m-%d')}

    Please ensure to return the book by the due date.

    Thank you,
    Your Library Management System
    """)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade to a secure connection
            server.login(sender_email, sender_password)  # Log in
            server.send_message(msg)  # Send the email
            print(f"Email sent to {user_email} successfully!")

    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    user_email = 'hpkgwork@gmail.com'  # Replace with the recipient's Gmail address
    book_title = 'The Great Gatsby'
    issue_date = datetime.now()

    send_email(user_email, book_title, issue_date, due_date)
