import uuid
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from brendan_labels import brendan_labels

def generate_gmail_filters_xml(parent_label, labels_array):
    feed = Element('feed', {'xmlns': 'http://www.w3.org/2005/Atom', 'xmlns:apps': 'http://schemas.google.com/apps/2006'})
    title = SubElement(feed, 'title')
    title.text = 'Mail Filters'
    id_ = SubElement(feed, 'id')
    id_.text = 'tag:mail.google.com,2008:filters:' + str(uuid.uuid4())
    updated = SubElement(feed, 'updated')
    updated.text = '2024-03-17T02:00:05Z'
    author = SubElement(feed, 'author')
    name = SubElement(author, 'name')
    name.text = 'Brendan O\'Brien'
    email = SubElement(author, 'email')
    email.text = 'obrienpbrendan@gmail.com'

    for label_info in labels_array:
        if not label_info.get('search_terms', None):
            continue
        
        entry = SubElement(feed, 'entry')
        category = SubElement(entry, 'category', {'term': 'filter'})
        title = SubElement(entry, 'title')
        title.text = 'Mail Filter'
        id_ = SubElement(entry, 'id')
        id_.text = 'tag:mail.google.com,2008:filter:' + str(uuid.uuid4())
        updated = SubElement(entry, 'updated')
        updated.text = '2024-03-17T02:00:05Z'
        content = SubElement(entry, 'content')

        # Construct search terms and avoid strings
        hasTheWord = ' OR '.join(['"%s"' % term for term in label_info.get('search_terms', [])])
        doesNotHaveTheWord = ' OR '.join(['"%s"' % term for term in label_info.get('avoid', [])])

        if hasTheWord:
            SubElement(entry, 'apps:property', {'name': 'hasTheWord', 'value': hasTheWord})
        if doesNotHaveTheWord:
            SubElement(entry, 'apps:property', {'name': 'doesNotHaveTheWord', 'value': doesNotHaveTheWord})
        
        label_element = SubElement(entry, 'apps:property', {'name': 'label', 'value': f"{parent_label}/{label_info['name']}"})
        should_mark_as_read = SubElement(entry, 'apps:property', {'name': 'shouldMarkAsRead', 'value': 'true'})
        size_operator = SubElement(entry, 'apps:property', {'name': 'sizeOperator', 'value': 's_sl'})
        size_unit = SubElement(entry, 'apps:property', {'name': 'sizeUnit', 'value': 's_smb'})

    xml_str = tostring(feed, 'utf-8')
    pretty_xml_as_string = parseString(xml_str).toprettyxml()

    return pretty_xml_as_string


sample_labels_array = [
    { "name": "1Password", "search_terms": ["@1password.com"] },
    { "name": "AirBnb", "search_terms": ["@airbnb.com"] },
    { "name": "Amazon Gift Cards", "search_terms": ["gc-orders", "giftcardsales@giftcards.amazon.com"] },
    { "name": "Amazon", "search_terms": ["@amazon.com", "@audible.com", "@primevideo.com"], "avoid": ["gc-orders", "giftcardsales@giftcards.amazon.com"] },
    { "name": "American Express", "search_terms": ["americanexpress.com"] },
    { "name": "Anytime Mailbox", "search_terms": ["PostNet TX221"] },
    { "name": "Apple", "search_terms": [".apple.com", "Your receipt from Apple", "Find My app"], "avoid": ["FemFast", "Mavely"] },
]

if __name__ == "__main__":
    # Generate XML with dynamic IDs
    parent_label = "*2025"
    xml_output = generate_gmail_filters_xml(parent_label, brendan_labels)
    with open('brendan_gmail_filters.xml', 'w') as file:
        file.write(xml_output)
