"""Author-owned publication, writing, and revision dates; never inferred from Git."""
import datetime as dt
import re


DATE = re.compile(r'\d{4}-\d{2}-\d{2}\Z')
TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z')


def parse_post_time(value, field):
    """Accept calendar dates or timezone-aware timestamps without losing precision."""
    error = f'{field}: use YYYY-MM-DD or an ISO 8601 timestamp with a timezone, such as 2026-09-29T14:00:00-04:00'
    if isinstance(value, dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None or not TIMESTAMP.fullmatch(value.isoformat()):
            raise ValueError(error)
        return value
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            if DATE.fullmatch(value):
                return dt.date.fromisoformat(value)
            if TIMESTAMP.fullmatch(value):
                return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
    raise ValueError(error)


def publication_date(value):
    """Publication is a calendar date so news ordering never depends on a timezone."""
    if isinstance(value, dt.datetime) or not (isinstance(value, dt.date) or isinstance(value, str) and DATE.fullmatch(value)):
        raise ValueError('date: use a publication date in YYYY-MM-DD format')
    try:
        return value if isinstance(value, dt.date) else dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('date: use a valid publication date in YYYY-MM-DD format') from exc


def calendar_day(value):
    return value.date() if isinstance(value, dt.datetime) else value


def display_time(value):
    label = value.strftime('%b %d, %Y').replace(' 0', ' ')
    if isinstance(value, dt.datetime):
        clock = value.strftime('%H:%M:%S' if value.second or value.microsecond else '%H:%M')
        offset = value.strftime('%z')
        zone = 'UTC' if offset == '+0000' else 'UTC' + offset[:3] + ':' + offset[3:]
        label += f', {clock} {zone}'
    return label


def metadata_dates(meta, published):
    """Missing lifecycle dates describe the initial edition, never the build time.

    A date alone represents a whole calendar day: compare calendar days whenever
    either endpoint lacks a time. Compare instants only for two exact timestamps.
    """
    created = parse_post_time(meta['created'], 'created') if 'created' in meta else published
    updated = parse_post_time(meta['updated'], 'updated') if 'updated' in meta else published
    if calendar_day(created) > published:
        raise ValueError('created must be on or before the publication date')
    if calendar_day(updated) < published:
        raise ValueError('updated must be on or after the publication date')
    if isinstance(created, dt.datetime) and isinstance(updated, dt.datetime):
        reversed_order = updated < created
    else:
        reversed_order = calendar_day(updated) < calendar_day(created)
    if reversed_order:
        raise ValueError('updated must be on or after created')
    return {
        'created': created.isoformat(), 'updated': updated.isoformat(),
        'created_display': display_time(created), 'updated_display': display_time(updated),
        'created_inferred': 'created' not in meta, 'updated_explicit': 'updated' in meta,
        'show_publication_date': calendar_day(created) != published,
    }
