from app.utils.sample_data import BUSINESS_CYCLE_SAMPLE

def get_business_cycle():
    latest = BUSINESS_CYCLE_SAMPLE[-1]
    dist = {}
    for row in BUSINESS_CYCLE_SAMPLE:
        dist[row['light']] = dist.get(row['light'], 0) + 1
    return {'latest': latest, 'history': BUSINESS_CYCLE_SAMPLE, 'distribution': [{'light': k, 'count': v} for k,v in dist.items()], 'note': '目前採本地範例資料；服務層已獨立封裝，未來可替換為公開正式資料來源。'}
