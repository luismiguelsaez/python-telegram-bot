CREATE TABLE video_record (camera int, filename char(80) not null, frame int, file_type int, time_stamp timestamp(14), event_time_stamp timestamp(14), video_end boolean, event_ack boolean);
CREATE TABLE security (camera int, filename char(80) not null, frame int, file_type int, time_stamp timestamp(14), event_time_stamp timestamp(14), event_end boolean, event_ack boolean);
