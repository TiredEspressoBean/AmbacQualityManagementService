from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_weekly_order_report(user, order_data):
    subject = 'Your Weekly Order Status Report'
    html_message = render_to_string('tracker/email/weekly_report.html', {
        'user': user,
        'orders': order_data,
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        None,  # uses DEFAULT_FROM_EMAIL
        [user.email],
        html_message=html_message,
    )
