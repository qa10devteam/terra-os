import os, logging, httpx
logger = logging.getLogger(__name__)

def sync_offer_to_pipedrive(offer_id: str, title: str = '', env=os.environ) -> dict:
    api_key = env.get('PIPEDRIVE_API_KEY')
    if not api_key:
        logger.info('PIPEDRIVE_API_KEY missing')
        return {'status': 'skipped'}
    try:
        r = httpx.post(
            f'https://api.pipedrive.com/v1/deals?api_token={api_key}',
            json={'title': title or offer_id},
            timeout=10
        )
        return {'status': 'synced', 'deal_id': r.json().get('data', {}).get('id')}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
