import csv
import re
import os
from typing import Any, Dict, List

def format_name(name: str) -> str:
    """
    Formats attorney name. e.g. "LAST, FIRST M" -> "First M. Last"
    Capitalizes first letter of each name part.
    Handles single-letter middle initials.
    """
    parts = name.split(',')
    if len(parts) != 2:
        return name.title()  # Fallback for unexpected formats

    last_name_str, first_middle_str = parts
    
    # Capitalize last name(s), handling multi-word last names
    last_names = [p.capitalize() for p in last_name_str.strip().split()]

    # Capitalize first and middle name(s)
    first_middle_parts = first_middle_str.strip().split()
    formatted_first_middle = []
    for part in first_middle_parts:
        # Handle middle initials like "J" or "J."
        if len(part) == 1:
            formatted_first_middle.append(part.upper() + ".")
        elif len(part) == 2 and part.endswith('.'):
            formatted_first_middle.append(part.upper())
        else: # First name or multi-letter middle name
            formatted_first_middle.append(part.capitalize())

    return f"{' '.join(formatted_first_middle)} {' '.join(last_names)}"

def calculate_scores(attorneys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates the weighted composite score for each attorney.
    """
    # Normalize a metric using min-max scaling
    def normalize(values: List[float]) -> List[float]:
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return [0.0] * len(values)
        return [(v - min_val) / (max_val - min_val) for v in values]

    # Extract metrics for normalization
    approval_rates = [p["approval_rate"] for p in attorneys]
    speeds = [p["speed"] for p in attorneys]
    grant_volumes = [p["granted_cases"] for p in attorneys]
    app_volumes = [p["total_cases"] for p in attorneys]

    # Normalize metrics
    norm_approval_rates = normalize(approval_rates)
    norm_speeds = normalize(speeds)
    norm_grant_volumes = normalize([float(v) for v in grant_volumes])
    norm_app_volumes = normalize([float(v) for v in app_volumes])

    # Sample weights
    weights = {
        "approval_rate": 0.35,
        "speed": 0.25,
        "grant_volume": 0.25,
        "application_volume": 0.15,
    }
    print(f"Using weights: {weights}")

    for i, attorney in enumerate(attorneys):
        score = (
            weights["approval_rate"] * norm_approval_rates[i]
            + weights["speed"] * norm_speeds[i]
            + weights["grant_volume"] * norm_grant_volumes[i]
            + weights["application_volume"] * norm_app_volumes[i]
        )
        attorney["score"] = score * 100

    print("--- Attorneys before sorting ---")
    for attorney in attorneys:
        print(f"Name: {attorney['name']}, Score: {attorney['score']:.4f}")

    # Sort by score and re-rank
    attorneys.sort(key=lambda x: x["score"], reverse=True)

    print("--- Attorneys after sorting ---")
    for attorney in attorneys:
        print(f"Name: {attorney['name']}, Score: {attorney['score']:.4f}")

    for i, attorney in enumerate(attorneys):
        attorney["rank"] = i + 1

    return attorneys

def create_html_table_rows(attorneys: List[Dict[str, Any]]) -> str:
    """
    Generates HTML table rows from processed attorney data.
    """
    html_rows = []
    for i, attorney in enumerate(attorneys):
        rank = i + 1
        # Use the corrected formatting for the name
        name = format_name(attorney["name"])
        total_cases = attorney["total_cases"]
        granted_cases = attorney["granted_cases"]
        approval_rate = f'{attorney["approval_rate"] * 100:.2f}%'
        avg_pendency = attorney["avg_pendency"]

        html_rows.append(
            f'            <tr><td class="rank-cell">{rank}</td><td>{name}</td><td>{total_cases}</td><td>{granted_cases}</td><td>{approval_rate}</td><td>{avg_pendency}</td></tr>'
        )
    return "\n".join(html_rows)

def load_attorneys(csv_path: str) -> List[Dict[str, Any]]:
    """
    Reads attorney data from a CSV file.
    """
    attorneys = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as infile:
            # Skip the header row manually
            next(infile)
            reader = csv.reader(infile)
            for row in reader:
                if not row or len(row) < 6:
                    continue

                (
                    _,
                    attorney_name,
                    total_cases,
                    granted_cases,
                    _, # grant_rate - discarded
                    avg_pendency,
                ) = row[:6]

                try:
                    total_cases_val = int(total_cases)
                    granted_cases_val = int(granted_cases)
                    pendency = int(avg_pendency)

                    approval_rate = (
                        granted_cases_val / total_cases_val
                        if total_cases_val > 0
                        else 0
                    )

                    attorneys.append(
                        {
                            "name": attorney_name.strip(),
                            "total_cases": total_cases_val,
                            "granted_cases": granted_cases_val,
                            "approval_rate": approval_rate,
                            "avg_pendency": pendency,
                            "speed": 1.0 / pendency if pendency > 0 else 0,
                        }
                    )
                except (ValueError, ZeroDivisionError):
                    continue  # Skip rows with invalid data
    except FileNotFoundError:
        print(f"Error: The file {csv_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return attorneys

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

if __name__ == "__main__":
    # Assuming the script is run from the root of the superset project
    CSV_FILE_PATH = os.path.join("superset", "templates", "superset", "attorney.csv")
    HTML_FILE_PATH = os.path.join(
        "superset", "templates", "superset", "top_attorneys.html"
    )

    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: Cannot find CSV file at {CSV_FILE_PATH}")
    elif not os.path.exists(HTML_FILE_PATH):
        print(f"Error: Cannot find HTML file at {HTML_FILE_PATH}")
    else:
        attorneys_data = load_attorneys(CSV_FILE_PATH)
        if attorneys_data:
            scored_attorneys = calculate_scores(attorneys_data)
            new_rows_html = create_html_table_rows(scored_attorneys)
            update_html_file(HTML_FILE_PATH, new_rows_html)
        else:
            print("No data found in CSV to update the HTML file.") 