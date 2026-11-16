# Query recipes

Common invocations of `scripts/query_events.py` and `scripts/summarize_day.py`. All are stdout-only; compose with `| jq`, `| less`, `| wc -l` as needed.

## 1. Daily brief

```bash
python3 scripts/summarize_day.py today
python3 scripts/summarize_day.py 2026-04-17 --terse
python3 scripts/summarize_day.py --week 2026-W16
```

## 2. Commits filtered

```bash
# today's commits as a markdown table
python3 scripts/query_events.py --kind commit --date today --render table

# commits in .claude/ in the last 7 days
python3 scripts/query_events.py --kind commit --since 7.days.ago --domain .claude --render table

# only features from this week
python3 scripts/query_events.py --kind commit --since this_week --theme feature
```

## 3. Domain rollup

```bash
# commits per top-level domain today
python3 scripts/query_events.py --kind commit --date today --group-by domain

# commits per theme this week
python3 scripts/query_events.py --kind commit --since this_week --group-by theme
```

## 4. Errors and incidents

```bash
# all errors today
python3 scripts/query_events.py --kind error --date today

# errors + incidents in the last 30 days by severity
python3 scripts/query_events.py --kind error,incident --since 30.days.ago --group-by severity
```

## 5. Timeline render

```bash
# chronological bullet list of everything today
python3 scripts/query_events.py --date today --render timeline
```

## 6. Velocity sanity check

```bash
# sum of insertions by day this week
for d in $(python3 -c "import datetime; t=datetime.date.today(); [print((t-datetime.timedelta(days=i)).isoformat()) for i in range(7)]"); do
  echo -n "$d  "
  python3 scripts/query_events.py --kind commit --date "$d" --sum insertions
done
```

## 7. Raw JSON export

```bash
# for scripting / piping elsewhere
python3 scripts/query_events.py --kind commit --date today --render json
```

## 8. Composition with other skills

When another skill (e.g. `execution-tracer`) needs the commits in a task's time range:

```bash
python3 scripts/query_events.py --kind commit --since <task_start_iso> --until <task_end_iso> --render json
```

The JSON output is a list of event objects — each one has `sha`, `subject`, `theme`, `files_changed`, `push_state`, and the other canonical fields.
