import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

def get_links(url):
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get("https://www.immoweb.be/en")
    
    # Handle cookie consent
    shadow_host = driver.find_element(By.ID, 'usercentrics-root')
    root = driver.execute_script('return arguments[0].shadowRoot', shadow_host)
    cookie_button = root.find_element(By.CSS_SELECTOR, '[data-testid=uc-accept-all-button]')
    cookie_button.click()

    # Search for properties
    driver.get(url)
    
    # Request page content
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract links to property listings
    links = [elem.get("href") for elem in soup.find_all("a", attrs={"class": "card__title-link"})]
    if not links:
        print("No properties found.")
        return None
    
    df = pd.DataFrame(links,columns=["Property Links"])
    df.to_csv('Links.csv', index=False)

    print("Links saved to Links.csv")

def scrape_property_details(filename):
    # Set up the Selenium driver
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get("https://www.immoweb.be/en")
    
    # Handle cookie consent
    shadow_host = driver.find_element(By.ID, 'usercentrics-root')
    root = driver.execute_script('return arguments[0].shadowRoot', shadow_host)
    cookie_button = root.find_element(By.CSS_SELECTOR, '[data-testid=uc-accept-all-button]')
    cookie_button.click()
    
    df = pd.read_csv(filename)
    links_file = df["Property Links"].tolist()
    all_property_data = []

    # Iterate through each link
    for link in links_file:
        driver.get(link)
    
        property_details = {}
   
    # Extract address details
       
        address_full = driver.find_elements(By.XPATH, "//span[@class='classified__information--address-row']")
        property_details['house_address'] = address_full[0].text.strip()
        property_details["postal_code"]= link.split('/')[-2]
        #property_details['postal_code'] = address_full[1].text.split('—')[0].strip()
        #property_details['locality'] = address_full[1].text.split('—')[1].strip()
        property_details['locality']=link.split('/')[-3]
        p_id= driver.find_element(By.XPATH,'//*[@id="classified-header"]/div/div/div[2]/div[1]/div[1]')
        property_details['ID']= p_id.text.split(':')[-1].strip()
        property_details['Type of proprty']= driver.find_element(By.CLASS_NAME,'classified__title').text.split(' ')[0].strip()
        property_details['Price']= driver.find_element(By.CLASS_NAME,'classified__price').text.split('-')[0].strip()
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

    #print(temp)
        property_data= property_details | temp  #adding two dict
        all_property_data.append(property_data)
        #print(all_property_data)
    # Clean up
    driver.quit()
    
    return all_property_data


# Function to extract required property information
def extract_property_info(all_property_data):
    
    all_extracted_values=[]
    
    # Define the keys to extract and their default values
    keys_to_extract = {
        'Property ID': 'ID',
        'Locality name': 'locality',
        'Postal code': 'postal_code',
        'Price':'Price' ,  
        'Type of property': 'Type of proprty',
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
            try:
                if source_key:
                    value = property_data.get(source_key)
                    if extracted_key == 'Type of property':
                    # Determine type based on content
                        if 'house' in (value or '').lower():
                            extracted_values[extracted_key] = 'House'
                        elif 'apartment' in (value or '').lower():
                            extracted_values[extracted_key] = 'Apartment'
                        else:
                            extracted_values[extracted_key] = 'Other'
                    elif extracted_key == 'Equipped kitchen (0/1)':
                    # Check for equipped kitchen terms
                        equipped_terms = ['installed', 'hyper equipped', 'semi equipped']
                        if any(term in (value or '').lower() for term in equipped_terms):
                            extracted_values[extracted_key] = 1
                        else:
                            extracted_values[extracted_key] = 0
                    elif extracted_key== 'Furnished (0/1)':
                        if value== "Yes":
                            extracted_values[extracted_key]= 1
                        else:
                            extracted_values[extracted_key]=0
                    elif extracted_key =='Open fire (0/1)':
                        if int(property_data.get(source_key, 0)) > 0:
                            extracted_values[extracted_key] = 1 
                        else:
                            extracted_values[extracted_key]= 0
                    elif extracted_key== 'Swimming pool (0/1)':
                        if value== "Yes":
                            extracted_values[extracted_key]=1
                        else:
                            extracted_values[extracted_key]=0     
                    else:
                        extracted_values[extracted_key] = value
                else:
                    extracted_values[extracted_key] = None
            except KeyError:
                extracted_values[extracted_key] = None

        all_extracted_values.append(extracted_values)
    return all_extracted_values

# Call function for save links in file
search_url = "https://www.immoweb.be/en/search/house/for-sale?countries=BE&page=1&orderBy=relevance"
property_data = get_links(search_url)

#call function for extract information from links
filename = 'Links.csv'
property_data_list = scrape_property_details(filename)
extracted_info = extract_property_info(property_data_list)

#save data in data.csv file
df_data= pd.DataFrame(extracted_info)
df_data.to_csv('data.csv', index=False)
print("data saved")
