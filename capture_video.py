import csv
import qscript


def main():
    with open("input.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(
            f,
            delimiter=";",
            quotechar='"'
        )

        for row in reader:
            print(f"\nProcessing: {row['Company Name']}")

            video_path = qscript.CaptureVideo(
                row["URL"],
                row["Company Name"],
                row["Language"],
                row["Country"],
                row["Postcode"],
                row["City"],
                row["Street"],
                row["HouseNo"]
            )

            if video_path:
                print(f"Video saved: {video_path}")
            else:
                print(f"Failed: {row['Company Name']}")


if __name__ == "__main__":
    main()