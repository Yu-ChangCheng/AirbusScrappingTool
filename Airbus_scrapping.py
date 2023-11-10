import requests
import regex as re
from bs4 import BeautifulSoup

# Start a session to keep cookies
session = requests.Session()

# The login page URL where we will get the necessary hidden fields
login_page_url = 'https://spares.airbus.com/H380/spares/forms/airbusspares.sfcc?TYPE=33554433&REALMOID=06-f058e2ed-17ab-45f1-bb0e-7043e7d379a0&GUID=&SMAUTHREASON=0&METHOD=GET&SMAGENTNAME=-SM-0cO6cUNMiUwYNDzYU0OOYryO02bybOYdV6ILdMqcd9Wfslw4Uu72wEVBl4IEzcb4CagWezrDK388Y5MhkGOqONFXuzVyJ8o%2f&TARGET=-SM-https%3a%2f%2fspares%2eairbus%2ecom%2fportal%2f'
login_page_response = session.get(login_page_url)
login_page_soup = BeautifulSoup(login_page_response.text, 'html.parser')

# Extracting hidden fields from the form
hidden_inputs = login_page_soup.find_all("input", type="hidden")
form_data = {input.get("name"): input.get("value") for input in hidden_inputs}

# Add your login credentials
form_data['USER'] = 'L_Cheng'
form_data['PASSWORD'] = 'aA33456789!@#$%^&'

# Log in to the website and print the url
response = session.post(login_page_url, data=form_data)
print("Response_url : " + response.url)

# soup = BeautifulSoup(response.text, 'html.parser')
# print(soup.prettify())

# Assuming you have a Part Number to search for
part_number = 'D30665-709'

# Add the part number to the form data under the correct key
search_data = {
    'menu-id': 'single_part_inquiry',
    'mode': 'portal',
    'REQUEST': 'INQUIRY_SINGLE',
    'ACTION': 'INQUIRY',
    'E_PNR': part_number,
    'INTERCHANGEABLES':'TRUE'
}

# The action URL for the part number search, which you would get from the form's 'action' attribute
search_action_url = 'https://spares.airbus.com/portal/stocks/status/stocks.jsp.port'

# Submit the search request
search_response = session.post(search_action_url, data=search_data)

# Print the contents of the scrap page
# print("Scrap page content:")
# print(scrap_page_soup.prettify())

# Print the contents of the search results page
if search_response.status_code == 200:
    search_soup = BeautifulSoup(search_response.text, 'html.parser')
    print("Search complete, processing results.")
    print("Search results content:")
    # print(search_soup.prettify())
    with open("search_results.html", "w", encoding='utf-8') as file:
        file.write(search_soup.prettify())
    # ... Process results ...
else:
    print("Failed to search for the part number, status code:", search_response.status_code)

table = search_soup.find('table', {'class': 'portlet-table-collapse'})

part_numbers = []
interchangeability = []
part_number_pattern = re.compile(r"escape\('([^']+)'\)")


# Check if the table was found
if table:
    # Find all rows in the table
    rows = table.find_all('tr')
    
    # Iterate through each row
    for row in rows:
        # Find all span elements in the row
        spans = row.find_all('span')
        for span in spans:
            if span.has_attr('onmouseover'):
                onmouseover = span['onmouseover']
                match = part_number_pattern.search(onmouseover)
                if match:
                    extracted_number = match.group(1)
                    displayed_text = span.get_text(strip=True)
                    # Check if the extracted number matches the displayed text
                    if extracted_number == displayed_text:
                        part_numbers.append(extracted_number)

        # Find interchangeability image and determine its type
        inc_img = row.find('img', onmouseover=lambda x: x and 'interchangeable' in x)
        if inc_img:
            if 'One-way interchangeable' in inc_img['onmouseover']:
                interchangeability.append('One-way')
            elif 'Two-ways interchangeable' in inc_img['onmouseover']:
                interchangeability.append('Two-ways')
            else:
                interchangeability.append('Unknown')

# Print the results
print("Part Numbers:", part_numbers)
print("Interchangeability:", interchangeability)


# Close the session when done
# session.close()
