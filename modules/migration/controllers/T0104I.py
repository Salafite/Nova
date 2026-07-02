from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from modules.migration.services import migration_service
from packages.auth.deps import get_current_user

router = APIRouter(prefix='/api/v1/migration', tags=['Migration'],
                   dependencies=[Depends(get_current_user)])

@router.post('/upload')
def upload_csv(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    column_mapping: str = Form('{}'),
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, 'Only CSV files are accepted')
    import json
    try:
        mapping = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(400, 'Invalid column_mapping JSON')
    content = file.file.read().decode('utf-8-sig')
    preview = migration_service.upload_csv(entity_type, content, mapping)
    migration_service.store_preview(preview['batch_id'], preview.pop('sample', []))
    return preview

@router.post('/commit')
def commit(batch_id: int):
    try:
        return migration_service.commit(batch_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post('/rollback')
def rollback(batch_id: int):
    try:
        return migration_service.rollback(batch_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get('/batch/{batch_id}')
def get_batch(batch_id: int):
    batch = migration_service.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, 'Batch not found')
    return batch
