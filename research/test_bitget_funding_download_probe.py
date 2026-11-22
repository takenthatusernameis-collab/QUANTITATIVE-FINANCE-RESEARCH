import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from bitget_funding_download_probe import analyze_csv_stream, analyze_download


class BitgetDownloadProbeParserTests(unittest.TestCase):
    def test_csv_summary_counts_duplicates_and_invalid_rates(self):
        data = (
            "Funding Time,Funding Rate,Symbol\n"
            "2020-01-01 00:00:00,0.0001,BTCUSDT\n"
            "2020-01-01 00:00:00,0.0002,BTCUSDT\n"
            "2020-01-01 08:00:00,nan,BTCUSDT\n"
        )
        summary = analyze_csv_stream(io.StringIO(data))
        self.assertEqual(summary["row_count"], 3)
        self.assertEqual(summary["time_column"], "Funding Time")
        self.assertEqual(summary["rate_column"], "Funding Rate")
        self.assertEqual(summary["duplicate_timestamp_count"], 1)
        self.assertEqual(summary["invalid_rate_count"], 1)
        self.assertEqual(summary["first_timestamp_raw"], "2020-01-01 00:00:00")
        self.assertEqual(summary["last_timestamp_raw"], "2020-01-01 08:00:00")
        self.assertEqual(summary["rate_min"], 0.0001)
        self.assertEqual(summary["rate_max"], 0.0002)

    def test_download_file_hash_and_csv_summary(self):
        data = "timestamp,fundingRate\n1704067200000,0.0001\n1704096000000,-0.0002\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "funding.csv"
            path.write_text(data, encoding="utf-8")
            summary = analyze_download(path)
        self.assertEqual(summary["size_bytes"], len(data.encode()))
        self.assertEqual(len(summary["sha256"]), 64)
        self.assertEqual(summary["data_summary"]["row_count"], 2)
        self.assertEqual(summary["data_summary"]["duplicate_timestamp_count"], 0)

    def test_zip_funding_csv_is_summarized_without_extracting(self):
        data = "time,rate\n2021-01-01,0.01\n2021-01-02,-0.02\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "funding.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("rates.csv", data)
                archive.writestr("readme.txt", "sample")
            summary = analyze_download(path)
        self.assertEqual(summary["zip_entries"][0]["name"], "rates.csv")
        self.assertEqual(summary["data_summary"]["row_count"], 2)
        self.assertEqual(summary["data_summary"]["rate_min"], -0.02)
        self.assertEqual(summary["data_summary"]["rate_max"], 0.01)


if __name__ == "__main__":
    unittest.main()
