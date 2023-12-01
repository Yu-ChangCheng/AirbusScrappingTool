import requests
import regex as re
from bs4 import BeautifulSoup
import pandas as pd
from queue import Queue
import datetime

# Use a list for master part numbers to search
master_part_numbers = ['2-1684', '898052', '980-6022-001', '1263A0000-03', '4063-16082-3', 'C16291AB', '5500C1ABF23A', '622-8973-104', '472088-1', 'H321BHM1']

# Initialize an empty list to collect DataFrames
dataframes_list = []

# Initialize one DataFrame to hold all data
combined_data_for_excel = pd.DataFrame({
    'INSCOR__PRIMARY_PRODUCT__C': [],
    'INSCOR__ALTERNATE_PRODUCT__C': [],
    'INSCOR__RELATIONSHIP__C': [],
    'INSCOR__DESCRIPTION__C': [],
    'INSCOR__SHOW_BOTH_SIDES_IN_PART_RESEARCH__C': []
})

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

# The action URL for the part number search, which you would get from the form's 'action' attribute
search_action_url = 'https://spares.airbus.com/portal/stocks/status/stocks.jsp.port'

def get_interchangeability_info(part_number):

    # Add the part number to the form data under the correct key
    search_data = {
        'menu-id': 'single_part_inquiry',
        'mode': 'portal',
        'REQUEST': 'INQUIRY_SINGLE',
        'ACTION': 'INQUIRY',
        'E_PNR': part_number,
        'INTERCHANGEABLES':'TRUE'
    }

    # Submit the search request
    search_response = session.post(search_action_url, data=search_data)
    
    # Print the contents of the search results page
    if search_response.status_code == 200:
        search_soup = BeautifulSoup(search_response.text, 'html.parser')
        print("Search complete, processing results. " + str(part_number))
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
    
    if len(part_numbers) == 1:
        return [], []
    else:
        return part_numbers[1:], interchangeability

# Process each master part number
for master_part_number in master_part_numbers:

    # Use a set to track which part numbers have been processed
    processed_part_numbers = set()
    # Use a set to check if any two-ways duplicates in the set
    two_way_relationships = set()
    # Use a queue to manage part numbers that need to be searched
    part_numbers_to_search = Queue()
    # Start with the primary part number
    part_numbers_to_search.put(master_part_number)
    
    # Data storage for Excel
    data_for_excel = {
        'INSCOR__PRIMARY_PRODUCT__C': [],
        'INSCOR__ALTERNATE_PRODUCT__C': [],
        'INSCOR__RELATIONSHIP__C': [],
        'INSCOR__DESCRIPTION__C': [],
        'INSCOR__SHOW_BOTH_SIDES_IN_PART_RESEARCH__C': []
    }
    
    while not part_numbers_to_search.empty():
        current_part_number = part_numbers_to_search.get()
        if current_part_number not in processed_part_numbers:
            processed_part_numbers.add(current_part_number)
            
            found_part_numbers, found_interchangeability = get_interchangeability_info(current_part_number)
            
            for alternate_product, relation in zip(found_part_numbers, found_interchangeability):
                
                # Check for two-way relationship and skip if it's already processed
               if relation == 'Two-ways' and (alternate_product, current_part_number) in two_way_relationships:
                   continue
    
               # Add the current two-way relationship to the set
               if relation == 'Two-ways':
                   two_way_relationships.add((current_part_number, alternate_product))
                
               data_for_excel['INSCOR__PRIMARY_PRODUCT__C'].append(current_part_number)
               data_for_excel['INSCOR__ALTERNATE_PRODUCT__C'].append(alternate_product)
               data_for_excel['INSCOR__RELATIONSHIP__C'].append(f"{relation} Interchangeable")
                
               # Add a description based on the relationship
               if relation == 'One-way':
                   description = f"{current_part_number} is REPL by {alternate_product} per IPC"
                   show_both_side = "FALSE"
               elif relation == 'Two-ways':
                   description = f"{current_part_number} & {alternate_product} are interchangeable per IPC"
                   show_both_side = "TRUE"
               else:
                   description = "Unknown relationship"
                   show_both_side = "N/A"
                   print("Error: Check the PN:" + current_part_number)
               data_for_excel['INSCOR__DESCRIPTION__C'].append(description)
               data_for_excel['INSCOR__SHOW_BOTH_SIDES_IN_PART_RESEARCH__C'].append(show_both_side)
        
               # Queue the alternate product for searching if it hasn't been processed
               if alternate_product not in processed_part_numbers:
                   part_numbers_to_search.put(alternate_product)
    
    # Create a DataFrame for the current master part number and add it to the list
    current_df = pd.DataFrame(data_for_excel)
    dataframes_list.append(current_df)

# Concatenate all DataFrames in the list into one DataFrame
combined_data_for_excel = pd.concat(dataframes_list, ignore_index=True)        
    

# Now save the combined data to one sheet in a single Excel file
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
excel_path = f'{timestamp}_Interchangeability.xlsx'
combined_data_for_excel.to_excel(excel_path, index=False)


print(f"Data saved to {excel_path}")

# Close the session when done
session.close()