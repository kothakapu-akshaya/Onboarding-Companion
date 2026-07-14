# Celery Integration Guide

This guide explains how to use Celery for asynchronous task processing in the corpus-te project.

## Overview

Celery has been integrated into the corpus-te project to handle:
- File processing (audio analysis, transcription)
- Background notifications (email alerts, processing status updates)
- Data analysis tasks (language detection, statistics generation)
- Maintenance operations (cleanup, database optimization)
- Report generation (daily reports, user reports)

## Architecture

### Components
1. **Redis** - Message broker and result backend
2. **Celery Workers** - Process tasks in background
3. **Celery Beat** - Scheduler for periodic tasks
4. **Flower** - Web-based monitoring tool
5. **FastAPI App** - Queues tasks and provides task management endpoints

### Task Queues
- `default` - General purpose tasks
- `file_processing` - Audio/video processing tasks
- `notifications` - Email and SMS notifications  
- `data_analysis` - Content analysis and statistics
- `maintenance` - Cleanup and system maintenance

## Setup Instructions

### 1. Install Redis

For development, you can run Redis with Docker:
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Or install locally on Arch Linux:
```bash
sudo pacman -S redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. Set Environment Variables

Copy the example environment file and configure:
```bash
cp .env.example .env
```

Update these Celery-related variables in `.env`:
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=300
```

### 3. Start the Application Stack

#### Option A: Using Docker Compose (Recommended)
```bash
# Start all services (app, workers, beat, redis, postgres)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

#### Option B: Manual Setup
1. **Start Redis and PostgreSQL** (if not using Docker)

2. **Start the FastAPI application:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Start Celery workers:**
```bash
# General worker
celery -A app.core.celery_app worker --loglevel=info --queues=default,file_processing,data_analysis

# Notifications worker
celery -A app.core.celery_app worker --loglevel=info --queues=notifications --concurrency=2

# Maintenance worker
celery -A app.core.celery_app worker --loglevel=info --queues=maintenance --concurrency=1
```

4. **Start Celery Beat (for scheduled tasks):**
```bash
celery -A app.core.celery_app beat --loglevel=info
```

5. **Start Flower (optional monitoring):**
```bash
celery -A app.core.celery_app flower --port=5555
```

## Usage Examples

### 1. Process Audio File
```python
# Via API endpoint
POST /api/v1/tasks/process-audio/123
```

```python
# Direct task call
from app.tasks.file_processing import process_audio_file
task = process_audio_file.delay(record_id=123, file_path="/path/to/file.mp3")
```

### 2. Send Notification
```python
# Via API endpoint
POST /api/v1/tasks/send-notification
{
    "recipients": ["user@example.com"],
    "subject": "Processing Complete",
    "message": "Your file has been processed successfully."
}
```

### 3. Generate Reports
```python
# Via API endpoint
POST /api/v1/tasks/reports/daily
POST /api/v1/tasks/reports/user
```

### 4. Check Task Status
```python
# Via API endpoint
GET /api/v1/tasks/status/{task_id}
```

### 5. Monitor Active Tasks
```python
# Via API endpoint (admin only)
GET /api/v1/tasks/active
GET /api/v1/tasks/scheduled
```

## Task Categories

### File Processing Tasks
- `process_audio_file` - Process uploaded audio files
- `upload_to_storage` - Upload files to object storage

### Notification Tasks
- `send_email` - Send email notifications
- `send_processing_complete_notification` - Notify when processing is done
- `send_bulk_notification` - Send notifications to multiple users
- `send_system_alert` - Send system alerts to administrators

### Data Analysis Tasks
- `analyze_audio_content` - Perform speech recognition and analysis
- `generate_corpus_statistics` - Generate comprehensive statistics
- `batch_language_detection` - Detect language for multiple records

### Maintenance Tasks
- `cleanup_old_files` - Clean up old temporary files
- `optimize_database` - Perform database maintenance
- `health_check` - Check system health
- `backup_database` - Create database backups

### Report Tasks
- `generate_daily_report` - Generate daily activity reports
- `generate_user_report` - Generate user-specific reports
- `generate_system_health_report` - Generate system health reports
- `export_user_data` - Export user data for GDPR compliance

## Scheduled Tasks

The following tasks run automatically:
- **File cleanup** - Every hour (cleanup old failed uploads)
- **Daily reports** - Every day at midnight
- **Health checks** - Can be configured as needed

## Monitoring

### Flower Web Interface
Access Flower at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Queue lengths
- Task execution times

### API Endpoints
- `GET /api/v1/tasks/active` - List active tasks
- `GET /api/v1/tasks/scheduled` - List scheduled tasks
- `GET /api/v1/tasks/status/{task_id}` - Get task status
- `DELETE /api/v1/tasks/cancel/{task_id}` - Cancel a task

### Logs
- Application logs: `logs/app.log`
- Celery worker logs: Docker Compose logs or systemd logs
- Redis logs: Check Redis configuration

## Error Handling

### Task Failures
- Failed tasks are logged with full error details
- Database records are updated with failure status
- System alerts are sent for critical failures
- Tasks can be retried automatically (configured per task)

### Dead Letter Queue
Configure dead letter queues for failed tasks:
```python
# In celery configuration
task_routes = {
    'app.tasks.*': {
        'queue': 'default',
        'routing_key': 'default',
        'exchange': 'default',
        'exchange_type': 'direct',
        'delivery_mode': 2,
    }
}
```

## Performance Tuning

### Worker Configuration
- Adjust worker concurrency based on CPU cores
- Use separate workers for different task types
- Configure memory limits and task time limits

### Queue Configuration
- Use priority queues for urgent tasks
- Set appropriate prefetch values
- Configure task routing based on complexity

### Redis Configuration
- Set appropriate memory limits
- Configure persistence settings
- Use Redis clustering for high availability

## Production Deployment

### Docker Deployment
Use the provided `docker-compose.yml` with adjustments:
- Set appropriate resource limits
- Configure persistent volumes
- Use Redis sentinel or cluster
- Set up log aggregation

### Kubernetes Deployment
Example deployments for:
- Redis cluster
- Celery workers (horizontal pod autoscaler)
- Celery beat (single replica)
- Application pods

### Security Considerations
- Use Redis AUTH in production
- Secure inter-service communication
- Implement task result encryption for sensitive data
- Set up proper firewall rules

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   - Check Redis is running: `redis-cli ping`
   - Verify connection URL in environment variables
   - Check firewall settings

2. **Tasks Not Being Processed**
   - Check if workers are running: `celery -A app.core.celery_app inspect active`
   - Verify queue routing configuration
   - Check worker logs for errors

3. **Memory Issues**
   - Monitor worker memory usage
   - Adjust worker concurrency
   - Implement task chunking for large datasets

4. **Database Connection Issues**
   - Check database connectivity from workers
   - Verify database URL in environment
   - Check connection pool settings

### Debugging Commands
```bash
# Check active tasks
celery -A app.core.celery_app inspect active

# Check scheduled tasks
celery -A app.core.celery_app inspect scheduled

# Check worker statistics
celery -A app.core.celery_app inspect stats

# Purge all tasks from queue
celery -A app.core.celery_app purge

# Monitor tasks in real-time
celery -A app.core.celery_app events
```

## API Examples

### Start Audio Processing
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/process-audio/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Check Task Status
```bash
curl -X GET "http://localhost:8000/api/v1/tasks/status/task-id-here" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Send Notification
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/send-notification" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["user@example.com"],
    "subject": "Test Notification",
    "message": "This is a test message"
  }'
```

### Generate User Report
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/reports/user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-05-01",
    "end_date": "2025-05-31"
  }'
```

This integration provides a robust foundation for handling background tasks in your Indic languages corpus collection application.
