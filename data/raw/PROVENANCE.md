# Dataset provenance

The evaluation dataset was supplied in the legacy KOLAS evaluation package as an XLSX workbook.

- Original workbook SHA-256: `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a`
- Original workbook row count: 843 data rows
- Original workbook columns: 11
- Transfer representation: pandas-loaded workbook -> UTF-8 CSV -> bzip2
- Transfer representation SHA-256: `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a`
- Transfer representation size: 52,817 bytes

The compressed CSV is a transport/processing representation, not byte-identical to the original XLSX.
The evaluation manifest hashes the exact representation used for a run. The original workbook hash is retained here for audit traceability.
