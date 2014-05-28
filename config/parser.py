#
# Copyright (c) 2013-2014 QuarksLab.
# This file is part of IRMA project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the top-level directory
# of this distribution and at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# No part of the project, including this file, may be copied,
# modified, propagated, or distributed except according to the
# terms contained in the LICENSE file.

import os
from celery.schedules import crontab
from kombu import Queue
from lib.irma.configuration.ini import TemplatedConfiguration

# ==========
#  Template
# ==========

template_frontend_config = {
    'mongodb': [
        ('host', TemplatedConfiguration.string, None),
        ('port', TemplatedConfiguration.integer, 27017),
        ('dbname', TemplatedConfiguration.string, None),
        ],
    'collections': [
        ('scan_info', TemplatedConfiguration.string, None),
        ('scan_results', TemplatedConfiguration.string, None),
        ('scan_ref_results', TemplatedConfiguration.string, None),
        ('scan_files', TemplatedConfiguration.string, None),
        ('scan_filedata', TemplatedConfiguration.string, None),
        ('scan_file_fs', TemplatedConfiguration.string, None),
        ],
    'celery_brain': [
        ('timeout', TemplatedConfiguration.integer, 10),
        ],
    'celery_frontend': [
        ('timeout', TemplatedConfiguration.integer, 10),
        ],
    'broker_brain': [
        ('host', TemplatedConfiguration.string, None),
        ('port', TemplatedConfiguration.integer, 5672),
        ('vhost', TemplatedConfiguration.string, None),
        ('username', TemplatedConfiguration.string, None),
        ('password', TemplatedConfiguration.string, None),
        ('queue', TemplatedConfiguration.string, None),
        ],
    'broker_frontend': [
        ('host', TemplatedConfiguration.string, None),
        ('port', TemplatedConfiguration.integer, 5672),
        ('vhost', TemplatedConfiguration.string, None),
        ('username', TemplatedConfiguration.string, None),
        ('password', TemplatedConfiguration.string, None),
        ('queue', TemplatedConfiguration.string, None),
        ],
    'backend_brain': [
        ('host', TemplatedConfiguration.string, None),
        ('port', TemplatedConfiguration.integer, 6379),
        ('db', TemplatedConfiguration.integer, None),
        ],
    'ftp_brain': [
        ('host', TemplatedConfiguration.string, None),
        ('port', TemplatedConfiguration.integer, 21),
        ('username', TemplatedConfiguration.string, None),
        ('password', TemplatedConfiguration.string, None),
        ],
    'cron_frontend': [
        ('clean_db_scan_info_max_age', TemplatedConfiguration.integer, 100),
        ('clean_db_scan_file_max_age', TemplatedConfiguration.integer, 2),
        ('clean_db_cron_hour', TemplatedConfiguration.string, '0'),
        ('clean_db_cron_minute', TemplatedConfiguration.string, '0'),
        ('clean_db_cron_day_of_week', TemplatedConfiguration.string, '*'),
        ],
}

cwd = os.path.abspath(os.path.dirname(__file__))
cfg_file = "{0}/{1}".format(cwd, "frontend.ini")
frontend_config = TemplatedConfiguration(cfg_file, template_frontend_config)


# ===============
#  Celery helper
# ===============

def _conf_celery(app, broker, backend=None, queue=None):
    app.conf.update(
        BROKER_URL=broker,
        CELERY_ACCEPT_CONTENT=['json'],
        CELERY_TASK_SERIALIZER='json',
        CELERY_RESULT_SERIALIZER='json'
        )
    if backend is not None:
        app.conf.update(CELERY_RESULT_BACKEND=backend)

    if queue is not None:
        app.conf.update(
            CELERY_DEFAULT_QUEUE=queue,
            # delivery_mode=1 enable transient mode
            # (don't survive to a server restart)
            CELERY_QUEUES=(Queue(queue, routing_key=queue),)
            )
    return


def conf_brain_celery(app):
    broker = get_brain_broker_uri()
    backend = get_brain_backend_uri()
    queue = frontend_config.broker_brain.queue
    _conf_celery(app, broker, backend, queue)


def conf_frontend_celery(app):
    broker = get_frontend_broker_uri()
    queue = frontend_config.broker_frontend.queue
    _conf_celery(app, broker, queue=queue)
    # add celerybeat conf only for frontend app
    cron_cfg = frontend_config['cron_frontend']
    app.conf.update(
        CELERYBEAT_SCHEDULE={
            # Database clean
            'clean_db': {
                'task': 'frontend.tasks.clean_db',
                'schedule': crontab(
                    hour=cron_cfg['clean_db_cron_hour'],
                    minute=cron_cfg['clean_db_cron_minute'],
                    day_of_week=cron_cfg['clean_db_cron_day_of_week']
                ),
                'args': (),
            },
        },
        CELERY_TIMEZONE='UTC'
    )


def get_db_uri():
    host = frontend_config.mongodb.host
    port = frontend_config.mongodb.port
    return "mongodb://{host}:{port}/".format(host=host, port=port)


def get_brain_celery_timeout():
    return frontend_config.celery_brain.timeout


def get_frontend_celery_timeout():
    return frontend_config.celery_admin.timeout


# =================
#  Backend helpers
# =================

def _get_backend_uri(backend_config):
    host = backend_config.host
    port = backend_config.port
    db = backend_config.db
    return "redis://{host}:{port}/{db}".format(host=host,
                                               port=port,
                                               db=db)


def get_brain_backend_uri():
    return _get_backend_uri(frontend_config.backend_brain)


# ================
#  Broker helpers
# ================

def _get_broker_uri(broker_config):
    user = broker_config.username
    pwd = broker_config.password
    host = broker_config.host
    port = broker_config.port
    vhost = broker_config.vhost
    return "amqp://{user}:{pwd}@{host}:{port}/{vhost}".format(user=user,
                                                              pwd=pwd,
                                                              host=host,
                                                              port=port,
                                                              vhost=vhost)


def get_brain_broker_uri():
    return _get_broker_uri(frontend_config.broker_brain)


def get_frontend_broker_uri():
    return _get_broker_uri(frontend_config.broker_frontend)
