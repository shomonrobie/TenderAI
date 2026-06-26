"""
Bangladesh Divisions, Districts, and Upazilas Complete Database
"""

# Divisions of Bangladesh
DIVISIONS = [
    "Dhaka", "Chittagong", "Rajshahi", "Khulna", 
    "Barisal", "Sylhet", "Rangpur", "Mymensingh"
]

# Complete Districts by Division
DIVISION_DISTRICTS = {
    "Dhaka": [
        "Dhaka", "Gazipur", "Narayanganj", "Tangail", "Kishoreganj", 
        "Manikganj", "Munshiganj", "Narsingdi", "Faridpur", "Gopalganj", 
        "Madaripur", "Rajbari", "Shariatpur"
    ],
    "Chittagong": [
        "Chittagong", "Cox's Bazar", "Rangamati", "Bandarban", "Khagrachhari", 
        "Feni", "Lakshmipur", "Noakhali", "Comilla", "Brahmanbaria", "Chandpur"
    ],
    "Rajshahi": [
        "Rajshahi", "Natore", "Chapainawabganj", "Naogaon", "Pabna", 
        "Sirajganj", "Bogra", "Joypurhat"
    ],
    "Khulna": [
        "Khulna", "Bagerhat", "Satkhira", "Jessore", "Jhenaidah", 
        "Magura", "Narail", "Kushtia", "Chuadanga", "Meherpur"
    ],
    "Barisal": [
        "Barisal", "Bhola", "Patuakhali", "Barguna", "Jhalokati", "Pirojpur"
    ],
    "Sylhet": [
        "Sylhet", "Sunamganj", "Habiganj", "Moulvibazar"
    ],
    "Rangpur": [
        "Rangpur", "Dinajpur", "Kurigram", "Gaibandha", "Lalmonirhat", 
        "Nilphamari", "Panchagarh", "Thakurgaon"
    ],
    "Mymensingh": [
        "Mymensingh", "Jamalpur", "Netrokona", "Sherpur"
    ]
}

# Complete Upazilas by District
UPAZILAS = {
    # Dhaka District
    "Dhaka": [
        "Dhaka Sadar", "Dhamrai", "Dohar", "Keraniganj", "Nawabganj", "Savar", "Tejgaon", "Gulshan", "Mirpur", "Mohammadpur"
    ],
    # Gazipur District
    "Gazipur": [
        "Gazipur Sadar", "Kaliakair", "Kaliganj", "Kapasia", "Sreepur"
    ],
    # Narayanganj District
    "Narayanganj": [
        "Narayanganj Sadar", "Araihazar", "Bandar", "Rupganj", "Sonargaon"
    ],
    # Bhola District
    "Bhola": [
        "Bhola Sadar", "Borhanuddin", "Char Fasson", "Daulatkhan", "Lalmohan", "Manpura", "Tazumuddin"
    ],
    # Barisal District
    "Barisal": [
        "Barisal Sadar", "Agailjhara", "Babuganj", "Bakerganj", "Banaripara", "Gaurnadi", "Hizla", "Mehendiganj", "Muladi", "Wazirpur"
    ],
    # Chittagong District
    "Chittagong": [
        "Chittagong Sadar", "Anwara", "Banshkhali", "Boalkhali", "Chandanaish", "Fatikchhari", "Hathazari", "Lohagara", "Mirsharai", "Patiya", "Rangunia", "Raozan", "Sandwip", "Satkania", "Sitakunda"
    ],
    # Cox's Bazar District
    "Cox's Bazar": [
        "Cox's Bazar Sadar", "Chakaria", "Kutubdia", "Maheshkhali", "Ramu", "Teknaf", "Ukhia", "Pekua"
    ],
    # Rajshahi District
    "Rajshahi": [
        "Rajshahi Sadar", "Bagha", "Bagmara", "Charghat", "Durgapur", "Godagari", "Mohanpur", "Paba", "Puthia", "Tanore"
    ],
    # Khulna District
    "Khulna": [
        "Khulna Sadar", "Batiaghata", "Dacope", "Dumuria", "Dighalia", "Koyra", "Paikgachha", "Phultala", "Rupsha", "Terokhada"
    ],
    # Sylhet District
    "Sylhet": [
        "Sylhet Sadar", "Balaganj", "Beanibazar", "Bishwanath", "Companiganj", "Dakshin Surma", "Fenchuganj", "Golapganj", "Gowainghat", "Jaintiapur", "Kanaighat", "Osmani Nagar", "Zakiganj"
    ],
    # Rangpur District
    "Rangpur": [
        "Rangpur Sadar", "Badarganj", "Gangachara", "Kaunia", "Mithapukur", "Pirgachha", "Pirganj", "Taraganj"
    ],
    # Mymensingh District
    "Mymensingh": [
        "Mymensingh Sadar", "Bhaluka", "Dhobaura", "Fulbaria", "Gaffargaon", "Gauripur", "Haluaghat", "Ishwarganj", "Muktagachha", "Nandail", "Phulpur", "Trishal"
    ],
    # Comilla District
    "Comilla": [
        "Comilla Sadar", "Barura", "Brahmanpara", "Burichang", "Chandina", "Chauddagram", "Daudkandi", "Debidwar", "Homna", "Laksam", "Monohorgonj", "Meghna", "Muradnagar", "Nangalkot", "Titas"
    ],
    # Noakhali District
    "Noakhali": [
        "Noakhali Sadar", "Begumganj", "Chatkhil", "Companiganj", "Hatiya", "Kabirhat", "Senbagh", "Sonaimuri", "Subarnachar"
    ],
    # Feni District
    "Feni": [
        "Feni Sadar", "Chhagalnaiya", "Daganbhuiyan", "Parshuram", "Sonagazi"
    ],
    # Brahmanbaria District
    "Brahmanbaria": [
        "Brahmanbaria Sadar", "Ashuganj", "Bancharampur", "Bijoynagar", "Kasba", "Nabinagar", "Nasirnagar", "Sarail"
    ],
    # Chandpur District
    "Chandpur": [
        "Chandpur Sadar", "Faridganj", "Haimchar", "Haziganj", "Kachua", "Matlab Dakshin", "Matlab Uttar", "Shahrasti"
    ],
    # Lakshmipur District
    "Lakshmipur": [
        "Lakshmipur Sadar", "Raipur", "Ramganj", "Ramgati"
    ],
    # Bogra District
    "Bogra": [
        "Bogra Sadar", "Adamdighi", "Dhunat", "Dhupchanchia", "Gabtali", "Kahaloo", "Nandigram", "Sariakandi", "Shibganj", "Sonatala"
    ],
    # Pabna District
    "Pabna": [
        "Pabna Sadar", "Atgharia", "Bera", "Bhangura", "Chatmohar", "Faridpur", "Ishwardi", "Santhia", "Sujanagar"
    ],
    # Sirajganj District
    "Sirajganj": [
        "Sirajganj Sadar", "Belkuchi", "Chauhali", "Kamarkhanda", "Kazipur", "Raiganj", "Shahjadpur", "Tarash", "Ullahpara"
    ],
    # Jessore District
    "Jessore": [
        "Jessore Sadar", "Abhaynagar", "Bagherpara", "Chaugachha", "Jhikargachha", "Keshabpur", "Manirampur", "Sharsha"
    ],
    # Kushtia District
    "Kushtia": [
        "Kushtia Sadar", "Bheramara", "Daulatpur", "Khoksa", "Kumarkhali", "Mirpur"
    ],
    # Satkhira District
    "Satkhira": [
        "Satkhira Sadar", "Assasuni", "Debhata", "Kalaroa", "Kaliganj", "Shyamnagar", "Tala"
    ],
    # Jhenaidah District
    "Jhenaidah": [
        "Jhenaidah Sadar", "Harinakunda", "Kaliganj", "Kotchandpur", "Maheshpur", "Shailkupa"
    ],
    # Natore District
    "Natore": [
        "Natore Sadar", "Bagatipara", "Baraigram", "Gurudaspur", "Lalpur", "Singra", "Naldanga"
    ],
    # Naogaon District
    "Naogaon": [
        "Naogaon Sadar", "Atrai", "Badalgachhi", "Dhamoirhat", "Manda", "Mohadevpur", "Niamatpur", "Patnitala", "Porsha", "Raninagar", "Sapahar"
    ],
    # Dinajpur District
    "Dinajpur": [
        "Dinajpur Sadar", "Birampur", "Birganj", "Bochaganj", "Chirirbandar", "Phulbari", "Ghoraghat", "Hakimpur", "Kaharole", "Khansama", "Nawabganj", "Parbatipur"
    ],
    # Thakurgaon District
    "Thakurgaon": [
        "Thakurgaon Sadar", "Baliadangi", "Haripur", "Pirganj", "Ranisankail"
    ],
    # Panchagarh District
    "Panchagarh": [
        "Panchagarh Sadar", "Atwari", "Boda", "Debiganj", "Tetulia"
    ],
    # Sunamganj District
    "Sunamganj": [
        "Sunamganj Sadar", "Bishwamvarpur", "Chhatak", "Dakshin Sunamganj", "Derai", "Dharampasha", "Dowarabazar", "Jagannathpur", "Jamalganj", "Sullah", "Tahirpur"
    ],
    # Habiganj District
    "Habiganj": [
        "Habiganj Sadar", "Ajmiriganj", "Baniachang", "Bahubal", "Chunarughat", "Lakhai", "Madhabpur", "Nabiganj", "Shayestaganj"
    ],
    # Moulvibazar District
    "Moulvibazar": [
        "Moulvibazar Sadar", "Barlekha", "Juri", "Kamalganj", "Kulaura", "Rajnagar", "Sreemangal"
    ],
    # Jamalpur District
    "Jamalpur": [
        "Jamalpur Sadar", "Bakshiganj", "Dewanganj", "Islampur", "Madarganj", "Melandaha", "Sarishabari"
    ],
    # Netrokona District
    "Netrokona": [
        "Netrokona Sadar", "Atpara", "Barhatta", "Durgapur", "Kalmakanda", "Kendua", "Khaliajuri", "Madan", "Mohanganj", "Purbadhala"
    ],
    # Sherpur District
    "Sherpur": [
        "Sherpur Sadar", "Jhenaigati", "Nakla", "Nalitabari", "Sreebardi"
    ],
    # Kishoreganj District
    "Kishoreganj": [
        "Kishoreganj Sadar", "Austagram", "Bajitpur", "Bhairab", "Hossainpur", "Itna", "Karimganj", "Katiadi", "Kuliarchar", "Nikli", "Pakundia", "Tarail"
    ],
    # Manikganj District
    "Manikganj": [
        "Manikganj Sadar", "Daulatpur", "Ghior", "Harirampur", "Saturia", "Shibalaya", "Singair"
    ],
    # Munshiganj District
    "Munshiganj": [
        "Munshiganj Sadar", "Gazaria", "Lohajang", "Sreenagar", "Serajdikhan", "Tongibari"
    ],
    # Narsingdi District
    "Narsingdi": [
        "Narsingdi Sadar", "Belabo", "Monohardi", "Palash", "Raipura", "Shibpur"
    ],
    # Faridpur District
    "Faridpur": [
        "Faridpur Sadar", "Alfadanga", "Bhanga", "Boalmari", "Charbhadrasan", "Madhukhali", "Nagarkanda", "Sadarpur", "Saltha"
    ],
    # Gopalganj District
    "Gopalganj": [
        "Gopalganj Sadar", "Kashiani", "Kotalipara", "Muksudpur", "Tungipara"
    ],
    # Madaripur District
    "Madaripur": [
        "Madaripur Sadar", "Kalkini", "Rajoir", "Shibchar"
    ],
    # Rajbari District
    "Rajbari": [
        "Rajbari Sadar", "Baliakandi", "Goalandaghat", "Pangsha", "Kalukhali"
    ],
    # Shariatpur District
    "Shariatpur": [
        "Shariatpur Sadar", "Bhedarganj", "Damudya", "Gosairhat", "Naria", "Zajira"
    ],
    # Tangail District
    "Tangail": [
        "Tangail Sadar", "Basail", "Bhuapur", "Delduar", "Ghatail", "Gopalpur", "Kalihati", "Madhupur", "Mirzapur", "Nagarpur", "Sakhipur", "Dhanbari"
    ],
    # Patuakhali District
    "Patuakhali": [
        "Patuakhali Sadar", "Bauphal", "Dashmina", "Galachipa", "Kalapara", "Mirzaganj", "Rangabali", "Dumki"
    ],
    # Barguna District
    "Barguna": [
        "Barguna Sadar", "Amtali", "Bamna", "Betagi", "Patharghata", "Taltali"
    ],
    # Jhalokati District
    "Jhalokati": [
        "Jhalokati Sadar", "Kanthalia", "Nalchity", "Rajapur"
    ],
    # Pirojpur District
    "Pirojpur": [
        "Pirojpur Sadar", "Bhandaria", "Kaukhali", "Mathbaria", "Nazirpur", "Nesarabad", "Zianagar"
    ],
    # Kurigram District
    "Kurigram": [
        "Kurigram Sadar", "Bhurungamari", "Char Rajibpur", "Chilmari", "Phulbari", "Nageshwari", "Rajarhat", "Raomari", "Ulipur"
    ],
    # Gaibandha District
    "Gaibandha": [
        "Gaibandha Sadar", "Fulchhari", "Gobindaganj", "Palashbari", "Sadullapur", "Saghata", "Sundarganj"
    ],
    # Lalmonirhat District
    "Lalmonirhat": [
        "Lalmonirhat Sadar", "Aditmari", "Hatibandha", "Kaliganj", "Patgram"
    ],
    # Nilphamari District
    "Nilphamari": [
        "Nilphamari Sadar", "Dimla", "Domar", "Jaldhaka", "Kishoreganj", "Saidpur"
    ],
    # Rangamati District
    "Rangamati": [
        "Rangamati Sadar", "Bagaichhari", "Barkal", "Juraichhari", "Kaptai", "Kawkhali", "Langadu", "Naniyachar", "Rajasthali"
    ],
    # Bandarban District
    "Bandarban": [
        "Bandarban Sadar", "Alikadam", "Naikhongchhari", "Rowangchhari", "Ruma", "Lama", "Thanchi"
    ],
    # Khagrachhari District
    "Khagrachhari": [
        "Khagrachhari Sadar", "Dighinala", "Lakshmichhari", "Mahalchhari", "Manikchhari", "Matiranga", "Panchhari", "Ramgarh"
    ]
}

def get_districts(division):
    """Get districts for a division"""
    return DIVISION_DISTRICTS.get(division, [])

def get_upazilas(district):
    """Get upazilas for a district"""
    return UPAZILAS.get(district, [])

def get_division_from_district(district):
    """Find division for a given district"""
    for division, districts in DIVISION_DISTRICTS.items():
        if district in districts:
            return division
    return None

def get_all_districts():
    """Get all districts"""
    all_districts = []
    for districts in DIVISION_DISTRICTS.values():
        all_districts.extend(districts)
    return sorted(all_districts)