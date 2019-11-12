## **MAIL**
[![](https://img.shields.io/badge/Project-mail-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Send email, attachment.

#### Install
    pip install tlib

#### Usage
```python
from libs import mail

if __name__ == "__main__":
    # Solution 1: SmtpServer + Mail
    obj_mail = mail.Mail(subject='', content='', m_from='', m_to='', m_cc='')
    smtp_1 = mail.SmtpServer(host='localhost', user='', password='', port=25)
    smtp_1.sendmail(obj_mail)
    
    # Solution 2: SmtpMailer
    smtp_2 = mail.SmtpMailer(sender='xy@gmail.com', server='smtp@gmail.com')
    smtp_2.sendmail('xy@outlook.com')
    
    # Solution 3: mutt sendmail, not recommended to use
    mail.mutt_sendmail(m_to='xy@outlook.com', subject='test', body='test content', attach='', content_is_html=False)
```

***
[1]: https://txu2008.github.io