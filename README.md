This service is one of admood advertisement project microservices that manage campaigns process in telegram platform,
such as create campaign, send push to publishers who can get this campaign due to category and some grade check
(grade check and chose publishers will calculate in core system) and so on.

Create campaign process is implemented by djangorestframework with Token authentication and all views inherit
GenericViewSet for more features expect serializer_class and queryset, like router and action,
serializers are inherit ModelSerializer and also have nested data validation and creation within.
For testing apis I use rest_framework APIClient, APITestCase with some fixtures data to populate test database 
for first use.

After campaign created, telegram bot should send a push to publishers who can receive campaign,

The next step is to monitor campaign banner views in different telegram channels and check some reach points,
like max_view that calculate by advertiser budget and one off the most important job is to don't let campaign views
pass this limit.
As user interface and send push and all other user communications I use python-telegram-bot to have a full-feature,
complex telegram bot, for monitor and read banner views I use Telethon library to have a telegram client
(real telegram user account logged in session),
because most of the functionality and access that client has we don't have in telegram bots.
(due to telegram rules bots have some limitations like getting user and messages, throttle, upload file size and etc..).
most of the monitor and push tasks are in background and we use celery and rabbitmq as message broker.
For getting updates from telegram we set webhook url and deployed by Nginx and uWSGI and database is Postgres. As issue
tracker we use sentry in all projects for getting more detail and some monthly reports that helped us very much to
optimize and refactor app logic and queries. As version control we use git and for software development we use CI/CD tool.

This is a summary of create, run, monitor campaigns in telegram and I'm responsible for whole these processes and I have
to  maintain, monitor workflow, check logs and issues to refactor bottlenecks and improve bot performance and queries.
I really like to make better queries and improve app logic by test and getting execution time and check benchmarks.

https://t.me/admood_bot/
