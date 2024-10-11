import requests
import selenium
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

def get_links():
    url= "https://www.immoweb.be/en/search/house/for-sale?countries=BE&page=1&orderBy=relevance"
    headers={ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
    response= requests.get(url,headers=headers)
    soup= BeautifulSoup(response.content,"html.parser")
    links = []
    for elem in soup.find_all("a", attrs={"class":"card__title-link"}):
        links.append(elem.get("href"))
    #print(links)
    return links

def scrape_property_details(links):
    

    # Set up the Selenium driver
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get("https://www.immoweb.be/en")
    
    # Handle cookie consent
    shadow_host = driver.find_element(By.ID, 'usercentrics-root')
    root = driver.execute_script('return arguments[0].shadowRoot', shadow_host)
    cookie_button = root.find_element(By.CSS_SELECTOR, '[data-testid=uc-accept-all-button]')
    cookie_button.click()
    
    all_property_data = []

    # Iterate through each link
    for link in links:
        driver.get(link)
        property_details = {}

        # Extract address details
        address_full = driver.find_elements(By.XPATH, "//span[@class='classified__information--address-row']")
        property_details['house_address'] = address_full[0].text.strip()
        property_details["postal_code"] = link.split('/')[-2]
        property_details['locality'] = link.split('/')[-3]
        
        p_id = driver.find_element(By.XPATH, '//*[@id="classified-header"]/div/div/div[2]/div[1]/div[1]')
        property_details['ID'] = p_id.text.split(':')[-1].strip()
        property_details['Type of property'] = driver.find_element(By.CLASS_NAME, 'classified__title').text.split(' ')[0].strip()
        property_details['Price'] = driver.find_element(By.CLASS_NAME, 'classified__price').text.split('-')[0].strip()
        
        temp = {}

        # Wait for the table to load and extract data
        WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "classified-table__header")))
        target_rows = driver.find_elements(By.XPATH, "//tr[@class='classified-table__row']")
        
        for row in target_rows:
            try:
                header_text = row.find_element(By.CLASS_NAME, 'classified-table__header').text.strip()
                data_text = row.find_element(By.CLASS_NAME, 'classified-table__data').text.split('\n')[0].strip()
                temp[header_text] = data_text
            except Exception as e:
                print(f"Error extracting data: {e}")  
                continue

        # Extract agency information
        try:
            property_details['agency'] = driver.find_element(By.CLASS_NAME, 'classified-customer__unique').get_attribute("innerHTML").split('\n')[0].strip()
        except:
            property_details['agency'] = 'Not Available'

        # Combine dictionaries
        property_data = {**property_details, **temp}
        all_property_data.append(property_data)

    # Clean up
    driver.quit()
    
    return all_property_data



def extract_property_info(all_property_data):
    all_extracted_values = []
    
    # Define the keys to extract and their default values
    keys_to_extract = {
        'Property ID': 'ID',
        'Locality name': 'locality',
        'Postal code': 'postal_code',
        'Price': 'Price',
        'Type of property': 'Type of property',
        'Subtype of property': None,  # Placeholder
        'Type of sale': None,  # Placeholder
        'Number of rooms': 'Bedrooms',
        'Living area (area in m²)': 'Living area',
        'Equipped kitchen (0/1)': 'Kitchen type',
        'Furnished (0/1)': 'Furnished',
        'Open fire (0/1)': 'How many fireplaces?',
        'Terrace (area in m² or null if no terrace)': 'Terrace surface',
        'Garden (area in m² or null if no garden)': 'Garden surface',
        'Number of facades': 'Number of frontages',
        'Swimming pool (0/1)': 'Swimming pool',
        'State of building': 'Building condition'
    }

    for property_data in all_property_data:
        extracted_values = {}
        for extracted_key, source_key in keys_to_extract.items():
            if source_key:
                value = property_data.get(source_key)
                # Additional logic based on extracted key
                if extracted_key == 'Type of property':
                    if 'house' in (value or '').lower():
                        extracted_values[extracted_key] = 'House'
                    elif 'apartment' in (value or '').lower():
                        extracted_values[extracted_key] = 'Apartment'
                    else:
                        extracted_values[extracted_key] = 'Other'
                elif extracted_key == 'Equipped kitchen (0/1)':
                    equipped_terms = ['installed', 'hyper equipped', 'semi equipped']
                    extracted_values[extracted_key] = 1 if any(term in (value or '').lower() for term in equipped_terms) else 0
                elif extracted_key == 'Furnished (0/1)':
                    extracted_values[extracted_key] = 1 if value == "Yes" else 0
                elif extracted_key == 'Open fire (0/1)':
                    extracted_values[extracted_key] = 1 if int(property_data.get(source_key, 0)) > 0 else 0
                elif extracted_key == 'Swimming pool (0/1)':
                    extracted_values[extracted_key] = 1 if value == "Yes" else 0
                else:
                    extracted_values[extracted_key] = value
            else:
                extracted_values[extracted_key] = None
        
        all_extracted_values.append(extracted_values)

    return all_extracted_values

# Example usage
link = get_links()
scrape= scrape_property_details(link)
extracted_info= extract_property_info(scrape)

df_data= pd.DataFrame(extracted_info)
df_data.to_csv('data.csv', index=False)
print("data saved")
