import csv
import re
import os
from typing import Any, Dict, List

def format_company_name(name: str) -> str:
    """
    Formats company name by capitalizing properly and handling common abbreviations.
    """
    # Handle common company abbreviations and formats
    name = name.strip()
    
    # Common abbreviations that should stay uppercase
    abbreviations = ['LLC', 'LLP', 'PC', 'PLLC', 'PA', 'PLC', 'LP', 'LLLP', 'INC', 'CORP', 'CORPORATION', 'CO', 'LTD', 'LIMITED']
    
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

def calculate_scores(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates the weighted composite score for each company.
    """
    # Normalize a metric using min-max scaling
    def normalize(values: List[float]) -> List[float]:
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return [0.0] * len(values)
        return [(v - min_val) / (max_val - min_val) for v in values]

    # Extract metrics for normalization
    grant_rates = [c["grant_rate"] for c in companies]
    speeds = [c["speed"] for c in companies]
    grant_volumes = [c["granted_cases"] for c in companies]
    app_volumes = [c["total_cases"] for c in companies]

    # Normalize metrics
    norm_grant_rates = normalize(grant_rates)
    norm_speeds = normalize(speeds)
    norm_grant_volumes = normalize([float(v) for v in grant_volumes])
    norm_app_volumes = normalize([float(v) for v in app_volumes])

    # Default weights for companies (same as firms)
    weights = {
        "grant_rate": 0.35,
        "speed": 0.25,
        "grant_volume": 0.25,
        "application_volume": 0.15,
    }
    print(f"Using weights: {weights}")

    for i, company in enumerate(companies):
        score = (
            weights["grant_rate"] * norm_grant_rates[i]
            + weights["speed"] * norm_speeds[i]
            + weights["grant_volume"] * norm_grant_volumes[i]
            + weights["application_volume"] * norm_app_volumes[i]
        )
        company["score"] = score * 100

    print("--- Companies before sorting ---")
    for company in companies:
        print(f"Name: {company['name']}, Score: {company['score']:.4f}")

    # Sort by score and re-rank
    companies.sort(key=lambda x: x["score"], reverse=True)

    print("--- Companies after sorting ---")
    for company in companies:
        print(f"Name: {company['name']}, Score: {company['score']:.4f}")

    for i, company in enumerate(companies):
        company["rank"] = i + 1

    return companies

def create_html_table_rows(companies: List[Dict[str, Any]]) -> str:
    """
    Generates HTML table rows from processed company data.
    """
    html_rows = []
    for i, company in enumerate(companies):
        rank = i + 1
        company_name = format_company_name(company["name"])
        total_cases = company["total_cases"]
        granted_cases = company["granted_cases"]
        grant_rate = f'{company["grant_rate"] * 100:.2f}%'
        avg_pendency = company["avg_pendency"]

        html_rows.append(
            f'            <tr>'
            f'<td class="rank-cell">{rank}</td>'
            f'<td class="company-name">{company_name}</td>'
            f'<td class="number-cell">{total_cases:,}</td>'
            f'<td class="number-cell">{granted_cases:,}</td>'
            f'<td class="percentage-cell">{grant_rate}</td>'
            f'<td class="days-cell">{avg_pendency:,}</td>'
            f'</tr>'
        )
    return "\n".join(html_rows)

def load_companies(csv_path: str) -> List[Dict[str, Any]]:
    """
    Reads company data from a CSV file.
    Expected CSV format:
    Company_Name, Total_Cases, Granted_Cases, Grant_Rate, Avg_Pendency
    """
    companies = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as infile:
            # Skip the header row manually
            next(infile)
            reader = csv.reader(infile)
            for row in reader:
                if not row or len(row) < 5:
                    continue

                (
                    company_name,
                    total_cases,
                    granted_cases,
                    grant_rate_csv,
                    avg_pendency,
                ) = row[:5]

                try:
                    total_cases_val = int(total_cases)
                    granted_cases_val = int(granted_cases)
                    grant_rate_csv_val = float(grant_rate_csv)  # Renamed to avoid confusion
                    pendency = int(avg_pendency)

                    # Calculate actual grant rate from cases
                    grant_rate_calculated = (
                        granted_cases_val / total_cases_val
                        if total_cases_val > 0
                        else 0
                    )

                    companies.append(
                        {
                            "name": company_name.strip(),
                            "total_cases": total_cases_val,
                            "granted_cases": granted_cases_val,
                            "grant_rate": grant_rate_calculated,
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
    return companies

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
    Creates a sample CSV file with dummy company data for testing.
    """
    sample_data = [
        ["Company_Name", "Total_Cases", "Granted_Cases", "Grant_Rate", "Avg_Pendency"],
        ["International Business Machines Corporation", "4850", "4100", "84.54", "520"],
        ["Microsoft Corporation", "3950", "3350", "84.81", "485"],
        ["Samsung Electronics Co Ltd", "3820", "3105", "81.28", "495"],
        ["Apple Inc", "3100", "2480", "80.00", "510"],
        ["Google LLC", "2850", "2280", "80.00", "475"],
        ["Intel Corporation", "2420", "1936", "80.00", "540"],
        ["Amazon Technologies Inc", "2080", "1664", "80.00", "515"],
        ["Tesla Inc", "1820", "1400", "76.92", "560"],
        ["Meta Platforms Inc", "1650", "1270", "76.97", "570"],
        ["NVIDIA Corporation", "1480", "1124", "75.95", "580"],
        ["Oracle Corporation", "1320", "1003", "75.98", "590"],
        ["Salesforce Inc", "1180", "885", "75.00", "600"],
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    print(f"Created sample CSV file: {csv_path}")

if __name__ == "__main__":
    # Assuming the script is run from the root of the superset project
    CSV_FILE_PATH = os.path.join("superset", "templates", "superset", "companies.csv")
    HTML_FILE_PATH = os.path.join(
        "superset", "templates", "superset", "top_companies.html"
    )

    # Create sample CSV if it doesn't exist
    if not os.path.exists(CSV_FILE_PATH):
        print(f"CSV file not found. Creating sample data at {CSV_FILE_PATH}")
        os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
        create_sample_csv(CSV_FILE_PATH)

    if not os.path.exists(HTML_FILE_PATH):
        print(f"Error: Cannot find HTML file at {HTML_FILE_PATH}")
    else:
        companies_data = load_companies(CSV_FILE_PATH)
        if companies_data:
            scored_companies = calculate_scores(companies_data)
            new_rows_html = create_html_table_rows(scored_companies)
            update_html_file(HTML_FILE_PATH, new_rows_html)
        else:
            print("No data found in CSV to update the HTML file.") 