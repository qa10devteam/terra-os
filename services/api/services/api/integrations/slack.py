import os, logging, httpx
logger = logging.getLogger(__name__)

def post_to_slack(message: str, channel: str = '#alerts', env=os.environ) -> dict:
    webhook = env.get('SLACK_WEBHOOK_URL')
    if not webhook:
        logger.info('SLACK_WEBHOOK_URL missing')
        return {'status': 'skipped'}
    try:
        r = httpx.post(webhook, json={'text': message, 'channel': channel}, timeout=10)
        return {'status': 'ok' if r.status_code == 200 else 'error'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
