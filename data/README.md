# Benchmark Data Repository

We welcome contributions of benchmark data! Please submit your results via **Pull Request**.

While we accept summary data, we strongly prefer **full format logs** that provide details for every test run. This allows for deeper analysis of failure modes and costs.

## Directory Layout

To keep things organized, please follow this directory structure for your submissions:

```text
data/
  $CONTRIBUTOR/
    YYYYMMDD/
      $USEFUL_NAME.yml
      $USEFUL_NAME.yml_meta.yml  (Optional)
```

- **$CONTRIBUTOR**: Your name or handle (e.g., `dwash`, `my-org`).
- **YYYYMMDD**: The date of the run (e.g., `20260217`).
- **$USEFUL_NAME.yml**: A descriptive name for the benchmark run (e.g., `hashline-more.yml`).

## Metadata Sidecars (`_meta.yml`)

You can provide an optional "sidecar" file to apply common metadata to all records in a data file.

If your data file is named `results.yml`, the sidecar **must** be named `results.yml_meta.yml`.

### How it works
Keys defined in the `_meta.yml` file are merged into every record found in the main data file.
- If a key is missing in the record, the sidecar value fills it in.
- If a key exists in the record, the sidecar value **overrides** it.

This is useful for defining invariant properties like the `commit_hash`, `edit_format`, or `test_cases` count once for an entire batch of runs.

**Example `hashlines.txt_meta.yml`:**
```yaml
test_cases: 14
edit_format: hash
commit_hash: 278813b-dirty
```
