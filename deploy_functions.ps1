# deploy_functions.ps1
$PROJECT_ID = "nate-digital-twin"
$REGION = "us-central1"
$TRANSCRIPT_BUCKET = "nate-digital-twin-transcript-cache"
$ANTHOLOGY_BUCKET = "nate-digital-twin-anthologies-djr"

Write-Host "--- Starting Deployment for Project: $PROJECT_ID ---" -ForegroundColor Cyan

# 1. Ensure Buckets Exist
function Ensure-Bucket ($bucket) {
    Write-Host "Checking bucket: $bucket..."
    $exists = gsutil ls -b gs://$bucket 2>$null
    if (-not $exists) {
        Write-Host "Creating bucket: $bucket" -ForegroundColor Yellow
        gsutil mb -p $PROJECT_ID -l $REGION gs://$bucket
    }
    else {
        Write-Host "Bucket exists." -ForegroundColor Green
    }
}

Ensure-Bucket $TRANSCRIPT_BUCKET
Ensure-Bucket $ANTHOLOGY_BUCKET

# 2. Deploy gcs_transcript_retriever
Write-Host "`n--- Deploying gcs_transcript_retriever ---" -ForegroundColor Cyan
cd gcs_transcript_retriever
gcloud functions deploy gcs-transcript-retriever `
    --gen2 `
    --runtime=python311 `
    --region=$REGION `
    --source=. `
    --entry-point=gcs_transcript_retriever `
    --trigger-http `
    --allow-unauthenticated `
    --set-env-vars=GCS_BUCKET_NAME=$TRANSCRIPT_BUCKET `
    --project=$PROJECT_ID
cd ..

# 3. Deploy transcript_processor_and_classifier
Write-Host "`n--- Deploying transcript_processor_and_classifier ---" -ForegroundColor Cyan
cd transcript_processor_and_classifier
gcloud functions deploy transcript-processor-and-classifier `
    --gen2 `
    --runtime=python311 `
    --region=$REGION `
    --source=. `
    --entry-point=transcript_processor_and_classifier `
    --trigger-http `
    --allow-unauthenticated `
    --project=$PROJECT_ID
cd ..

# 4. Deploy anthology_updater
Write-Host "`n--- Deploying anthology_updater ---" -ForegroundColor Cyan
cd anthology_updater
gcloud functions deploy anthology-updater `
    --gen2 `
    --runtime=python311 `
    --region=$REGION `
    --source=. `
    --entry-point=anthology_updater `
    --trigger-http `
    --allow-unauthenticated `
    --set-env-vars=ANTHOLOGY_BUCKET_NAME=$ANTHOLOGY_BUCKET `
    --project=$PROJECT_ID
cd ..

Write-Host "`n--- Deployment Complete ---" -ForegroundColor Green
Write-Host "Please capture the URLs above for the next step."
