-- Total duration of duplicate files
SELECT count(*), sum(total_duration) 
from (
    select 
        file_name, 
        sum(duration_seconds) - min(duration_seconds) as total_duration 
    from record 
    where duration_seconds is not null 
    group by file_name, file_size having count(*) > 1
) AS duplicate_files;


-- Compute audio and video duration for all records
SELECT sum(duration_seconds)/3600 from record where media_type = 'audio';
SELECT sum(duration_seconds)/3600 from record where media_type = 'video';


-- SELECT id from public.user WHERE phone = '+918106565763' LIMIT 10;


select file_url, uid, duration_seconds, file_name 
from record 
where 
    duration_seconds is null and
    (media_type = 'audio' OR media_type = 'video') and 
    file_url is not null and 
    file_url != '' and
    status = 'uploaded';

-- Get all file suffixes by splitting file_name on '.'
SELECT t.file_name, t.file_suffix FROM (
SELECT file_name, split_part(file_name, '.', -1) as file_suffix FROM record where media_type = 'audio' or media_type = 'video'
) as t where t.file_suffix NOT IN ('mp3', 'mp4', 'mov', 'MOV', 'm4a', 'jpg', 'jpeg', 'heif', 'png', 'webm', 'wav', 'mpeg', 'aac', 'MP4', 'opus', 'mkv', 'avi') and file_suffix is not null;
