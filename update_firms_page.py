import csv
import re
import os
from typing import Any, Dict, List

def format_firm_name(name: str) -> str:
    """
    Formats firm name by capitalizing properly and handling common abbreviations.
    """
    # Handle common law firm abbreviations and formats
    name = name.strip()
    
    # Common abbreviations that should stay uppercase
    abbreviations = ['LLC', 'LLP', 'PC', 'PLLC', 'PA', 'PLC', 'LP', 'LLLP']
    
    # Split into words and process
    words = name.split()
    formatted_words = []
    
    for word in words:
        # Check if it's a common abbreviation
        if word.upper() in abbreviations:
            formatted_words.append(word.upper())
        elif word in ['&', 'and', 'of', 'the', 'at']:
            # Keep conjunctions lowercase unless at start
            formatted_words.append(word.lower() if formatted_words else word.capitalize())
        else:
            # Capitalize normally
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)



def calculate_scores(firms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates the weighted composite score for each law firm.
    """
    # Normalize a metric using min-max scaling
    def normalize(values: List[float]) -> List[float]:
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return [0.0] * len(values)
        return [(v - min_val) / (max_val - min_val) for v in values]

    # Extract metrics for normalization
    grant_rates = [f["grant_rate"] for f in firms]
    speeds = [f["speed"] for f in firms]
    grant_volumes = [f["granted_cases"] for f in firms]
    app_volumes = [f["total_cases"] for f in firms]

    # Normalize metrics
    norm_grant_rates = normalize(grant_rates)
    norm_speeds = normalize(speeds)
    norm_grant_volumes = normalize([float(v) for v in grant_volumes])
    norm_app_volumes = normalize([float(v) for v in app_volumes])

    # Default weights for firms (same as attorneys)
    weights = {
        "grant_rate": 0.35,
        "speed": 0.25,
        "grant_volume": 0.25,
        "application_volume": 0.15,
    }
    print(f"Using weights: {weights}")

    for i, firm in enumerate(firms):
        score = (
            weights["grant_rate"] * norm_grant_rates[i]
            + weights["speed"] * norm_speeds[i]
            + weights["grant_volume"] * norm_grant_volumes[i]
            + weights["application_volume"] * norm_app_volumes[i]
        )
        firm["score"] = score * 100

    print("--- Firms before sorting ---")
    for firm in firms:
        print(f"Name: {firm['name']}, Score: {firm['score']:.4f}")

    # Sort by score and re-rank
    firms.sort(key=lambda x: x["score"], reverse=True)

    print("--- Firms after sorting ---")
    for firm in firms:
        print(f"Name: {firm['name']}, Score: {firm['score']:.4f}")

    for i, firm in enumerate(firms):
        firm["rank"] = i + 1

    return firms

def create_html_table_rows(firms: List[Dict[str, Any]]) -> str:
    """
    Generates HTML table rows from processed firm data.
    """
    html_rows = []
    for i, firm in enumerate(firms):
        rank = i + 1
        firm_name = format_firm_name(firm["name"])
        total_cases = firm["total_cases"]
        granted_cases = firm["granted_cases"]
        grant_rate = f'{firm["grant_rate"] * 100:.2f}%'
        avg_pendency = firm["avg_pendency"]

        html_rows.append(
            f'            <tr>'
            f'<td class="rank-cell">{rank}</td>'
            f'<td class="firm-name">{firm_name}</td>'
            f'<td class="number-cell">{total_cases:,}</td>'
            f'<td class="number-cell">{granted_cases:,}</td>'
            f'<td class="percentage-cell">{grant_rate}</td>'
            f'<td class="days-cell">{avg_pendency:,}</td>'
            f'</tr>'
        )
    return "\n".join(html_rows)

def load_firms(csv_path: str) -> List[Dict[str, Any]]:
    """
    Reads firm data from a CSV file.
    Expected CSV format:
    Firm_Name, Total_Cases, Granted_Cases, Grant_Rate, Avg_Pendency
    """
    firms = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as infile:
            # Skip the header row manually
            next(infile)
            reader = csv.reader(infile)
            for row in reader:
                if not row or len(row) < 5:
                    continue

                (
                    firm_name,
                    total_cases,
                    granted_cases,
                    grant_rate,
                    avg_pendency,
                ) = row[:5]

                try:
                    total_cases_val = int(total_cases)
                    granted_cases_val = int(granted_cases)
                    grant_rate = float(grant_rate)
                    pendency = int(avg_pendency)

                    grant_rate = (
                        granted_cases_val / total_cases_val
                        if total_cases_val > 0
                        else 0
                    )

                    firms.append(
                        {
                            "name": firm_name.strip(),
                            "total_cases": total_cases_val,
                            "granted_cases": granted_cases_val,
                            "grant_rate": grant_rate,
                            "avg_pendency": pendency,
                            "speed": 1.0 / pendency if pendency > 0 else 0,
                        }
                    )
                except (ValueError, ZeroDivisionError) as e:
                    print(f"Skipping row due to error: {e}, Row: {row}")
                    continue  # Skip rows with invalid data
    except FileNotFoundError:
        print(f"Error: The file {csv_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return firms

def update_html_file(html_path: str, new_tbody_content: str) -> None:
    """
    Replaces the <tbody> content of an HTML file with new content.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_tbody_section = f"<tbody>\n{new_tbody_content}\n          </tbody>"
    new_content, count = re.subn(
        r"<tbody.*?>.*?</tbody>", new_tbody_section, content, flags=re.DOTALL
    )

    if count > 0:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully updated the table in {html_path}")
    else:
        print(f"Error: Could not find a <tbody> section to replace in {html_path}")

def create_sample_csv(csv_path: str) -> None:
    """
    Creates a sample CSV file with dummy firm data for testing.
    """
    sample_data = [
        ["Firm_Name", "Total_Cases", "Granted_Cases", "Grant_Rate", "Avg_Pendency"],
        ["FISH & RICHARDSON P.C.", "2850", "2400", "84.21", "520"],
        ["FENWICK & WEST LLP", "1950", "1650", "84.62", "485"],
        ["WILSON SONSINI GOODRICH & ROSATI", "1820", "1485", "81.59", "495"],
        ["KILPATRICK TOWNSEND & STOCKTON LLP", "2100", "1680", "80.00", "510"],
        ["COOLEY LLP", "1650", "1320", "80.00", "475"],
        ["BAKER & BOTTS L.L.P.", "1420", "1136", "80.00", "540"],
        ["PERKINS COIE LLP", "1580", "1264", "80.00", "515"],
        ["SKADDEN ARPS SLATE MEAGHER & FLOM LLP", "1120", "862", "76.96", "560"],
        ["JONES DAY", "1050", "809", "77.05", "570"],
        ["GIBSON DUNN & CRUTCHER LLP", "980", "745", "76.02", "580"],
        ["DAVIS POLK & WARDWELL LLP", "920", "699", "75.98", "590"],
        ["KIRKLAND & ELLIS LLP", "880", "660", "75.00", "600"],
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    print(f"Created sample CSV file: {csv_path}")

if __name__ == "__main__":
    # Assuming the script is run from the root of the superset project
    CSV_FILE_PATH = os.path.join("superset", "templates", "superset", "firms.csv")
    HTML_FILE_PATH = os.path.join(
        "superset", "templates", "superset", "top_firms.html"
    )

    # Create sample CSV if it doesn't exist
    if not os.path.exists(CSV_FILE_PATH):
        print(f"CSV file not found. Creating sample data at {CSV_FILE_PATH}")
        os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
        create_sample_csv(CSV_FILE_PATH)

    if not os.path.exists(HTML_FILE_PATH):
        print(f"Error: Cannot find HTML file at {HTML_FILE_PATH}")
    else:
        firms_data = load_firms(CSV_FILE_PATH)
        if firms_data:
            scored_firms = calculate_scores(firms_data)
            new_rows_html = create_html_table_rows(scored_firms)
            update_html_file(HTML_FILE_PATH, new_rows_html)
        else:
            print("No data found in CSV to update the HTML file.") 