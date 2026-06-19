import asyncio
from email.utils import parsedate_to_datetime
from app.core.neo4j_repository import Neo4jRepository

async def fix_dates():
    repo = Neo4jRepository('12582952-7f59-4565-943a-9c0cde898ba3') 
    
    res = await repo.execute_read('MATCH (e:Email) WHERE e.tenant_id = $tenant_id RETURN e.id as id, e.date as date', {'tenant_id': '12582952-7f59-4565-943a-9c0cde898ba3'})
    
    updates = []
    for r in res:
        date_str = r['date']
        if date_str and not date_str.startswith('202'):
            try:
                dt = parsedate_to_datetime(date_str)
                iso_date = dt.isoformat()
                updates.append({'id': r['id'], 'iso_date': iso_date})
            except Exception as e:
                pass
                
    if updates:
        query = '''
        UNWIND $updates AS update
        MATCH (e:Email {id: update.id, tenant_id: $tenant_id})
        SET e.date = update.iso_date
        '''
        await repo.execute_write(query, {'tenant_id': '12582952-7f59-4565-943a-9c0cde898ba3', 'updates': updates})
        print(f'Fixed {len(updates)} email dates in Neo4j')
    else:
        print('No dates needed fixing')

asyncio.run(fix_dates())
