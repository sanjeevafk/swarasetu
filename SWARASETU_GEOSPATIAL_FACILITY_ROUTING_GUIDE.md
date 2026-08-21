# SwaraSetu Geospatial Facility Routing & Rural Health Directory Guide

This document provides a technical reference on how **SwaraSetu** handles offline geospatial localization, facility distance routing, automated ASHA worker alerts, and integration with India's official **Ayushman Bharat Digital Mission (ABDM) Health Facility Registry (HFR)**.

---

## 1. How Offline Location Works Without Internet

Rural primary healthcare workers and patients frequently operate in "media-dark" zones with **0% cellular data or broadband connectivity**. SwaraSetu is engineered to deliver accurate geospatial facility routing even in total network isolation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        OFFLINE DEVICE (0% Internet)                    │
│                                                                        │
│  [ GPS / NavIC Satellites ]                                            │
│            │ (Radio Waves / NMEA Sentences)                            │
│            ▼                                                           │
│  [ Device Hardware GPS Chip ]  ──▶  navigator.geolocation API          │
│                                              │                         │
│                                              ▼                         │
│                                [ Local Latitude & Longitude ]          │
│                                              │                         │
│                                              ▼                         │
│                               [ On-Device Haversine Distance Math ]     │
│                                              ▲                         │
│                                              │                         │
│  [ Pre-Bundled Offline Facility Directory (IndexedDB / mockPHCs.ts) ]  │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Satellite GPS Hardware (Zero Data Requirement)
- Modern Android smartphones and tablets contain dedicated hardware GPS/GLONASS/NavIC baseband chips.
- These chips receive passive radio frequency signals directly from orbital satellites (at 1575.42 MHz / L1 band).
- Position calculation (trilateration) occurs entirely on the local silicon chip using orbital ephemeris data.
- **Key Takeaway:** The operating system and web browser (`navigator.geolocation.getCurrentPosition()`) can determine exact WGS84 coordinates without SIM cards, cellular towers, Wi-Fi, or internet packets.

### 1.2 On-Device Spatial Computation (The Haversine Formula)
When an emergency (WHO IMCI Score 3 / Red) is identified offline, the local engine computes Great-Circle distances to all facilities in under **0.5 milliseconds** using the Haversine equation:

$$\Delta\sigma = 2 \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$

$$d = R \cdot \Delta\sigma$$

Where:
- $\phi_1, \phi_2$ = latitudes in radians
- $\Delta\phi = \phi_2 - \phi_1$
- $\Delta\lambda = \lambda_2 - \lambda_1$
- $R$ = Earth's mean radius ($6,371\text{ km}$)

In Python (`backend/app/services/phc_service.py`):
```python
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(6371.0 * c, 2)
```

---

## 2. Production vs. Prototype Data Sources

### 2.1 Official Production Source: Ayushman Bharat Health Facility Registry (HFR)
In a state-wide or national deployment, facility coordinates and personnel registries are ingested directly from the Government of India's official digital health repositories:

| National Repository | Managing Body | Data Provided | Ingestion Protocol |
|---|---|---|---|
| **Health Facility Registry (HFR)** | National Health Authority (NHA) / ABDM | 160,000+ Ayushman Arogya Mandirs, PHCs, CHCs, and District Hospitals with geo-coordinates, facility ID, services, and bed count. | REST API / NDHM Open Data Export |
| **Health Professional Registry (HPR)** | National Health Authority (NHA) / ABDM | Registered Medical Officers, Nurses, and Specialists mapped to facility IDs. | ABDM M1/M2 Tokenized Ingestion |
| **ASHA / ANM Village Roster** | National Health Mission (NHM) / State Health Societies | Village-level ASHA assignments, contact numbers, and sub-center linkages. | District Health Information System (DHIS2 / HMIS) |
| **National Emergency Ambulance (108 / 102)** | State Emergency Medical Services (GVK EMRI / BVG) | GPS fleet status, central ambulance dispatch queues, and district emergency lines. | Webhook / Computer-Aided Dispatch (CAD) |

### 2.2 Prototype Data Sources (Current Implementation)
For hackathon demonstration and offline simulation, the repository uses a realistic geographic model based on **Sitamarhi, Sheohar, and Muzaffarpur districts in North Bihar**:

1. **Coordinates:** Real geographical block centroids and hospital premises verified via OpenStreetMap.
2. **Landlines & STD Codes:** Real Indian telephone STD area codes (`06226` for Sitamarhi, `06290` for Sheohar, `06212` for Muzaffarpur).
3. **Emergency Numbers:** National standardized fallbacks (**108** for Ambulance, **104** for Telemedicine Support).

---

## 3. Seed Prototype Dataset Reference (North Bihar Baseline)

### 3.1 Primary Health Centres & Hospitals (`backend/scripts/seed_phc_data.py`)
```python
PHCS = [
    {
        "name": "Belsand Primary Health Center",
        "district": "Sitamarhi",
        "facility_type": "PHC",
        "phone": "+91-6226-282234",
        "latitude": 26.4468,
        "longitude": 85.3402,
        "is_24x7": True,
        "doctor_available": True,
        "hours": "24/7",
    },
    {
        "name": "Runnisaidpur Block Hospital",
        "district": "Sitamarhi",
        "facility_type": "CHC",
        "phone": "+91-6226-254410",
        "latitude": 26.3768,
        "longitude": 85.3852,
        "is_24x7": False,
        "doctor_available": False,
        "hours": "9 AM - 5 PM",
    },
    {
        "name": "Dumra Community Health Centre",
        "district": "Sitamarhi",
        "facility_type": "CHC",
        "phone": "+91-6226-224480",
        "latitude": 26.5868,
        "longitude": 85.3902,
        "is_24x7": True,
        "doctor_available": True,
        "hours": "24/7",
    },
    {
        "name": "Pupri Referral Hospital",
        "district": "Sitamarhi",
        "facility_type": "PHC",
        "phone": "+91-6226-260233",
        "latitude": 26.5068,
        "longitude": 85.6402,
        "is_24x7": True,
        "doctor_available": True,
        "hours": "24/7",
    },
    {
        "name": "Sursand Health Sub-Center",
        "district": "Sitamarhi",
        "facility_type": "SubCenter",
        "phone": "+91-6226-276118",
        "latitude": 26.6168,
        "longitude": 85.5402,
        "is_24x7": False,
        "doctor_available": False,
        "hours": "9 AM - 2 PM",
    },
    {
        "name": "Sheohar District Hospital",
        "district": "Sheohar",
        "facility_type": "District Hospital",
        "phone": "+91-6290-222100",
        "latitude": 26.5158,
        "longitude": 85.2911,
        "is_24x7": True,
        "doctor_available": True,
        "hours": "24/7",
    },
    {
        "name": "Muzaffarpur Sadar Hospital",
        "district": "Muzaffarpur",
        "facility_type": "District Hospital",
        "phone": "+91-6212-222214",
        "latitude": 26.1209,
        "longitude": 85.3647,
        "is_24x7": True,
        "doctor_available": True,
        "hours": "24/7",
    },
]
```

### 3.2 ASHA Field Worker Roster
```python
ASHA_WORKERS = [
    {"asha_name": "Sunita Devi", "phone": "+91-9876501201", "village": "Belsand", "district": "Sitamarhi"},
    {"asha_name": "Rekha Kumari", "phone": "+91-9876501202", "village": "Dumra", "district": "Sitamarhi"},
    {"asha_name": "Poonam Singh", "phone": "+91-9876501203", "village": "Runnisaidpur", "district": "Sitamarhi"},
    {"asha_name": "Anita Devi", "phone": "+91-9876501301", "village": "Sheohar", "district": "Sheohar"},
]
```

---

## 4. How to Change Region (Step-by-Step Customization)

To adapt SwaraSetu for any state (e.g. **Tamil Nadu**, **Kerala**, or **Jharkhand**), follow these 3 steps:

### Step 1: Update Frontend Map Defaults & Offline Directory

1. **Map Center (`src/components/PHCMap.tsx`):**
   ```typescript
   // Example 1: Madurai, Tamil Nadu
   const defaultCenter: [number, number] = [9.9252, 78.1198];

   // Example 2: Wayanad, Kerala
   const defaultCenter: [number, number] = [11.6854, 76.1320];

   // Example 3: Ranchi, Jharkhand
   const defaultCenter: [number, number] = [23.3441, 85.3096];
   ```

2. **Offline PHC Directory (`src/data/mockPHCs.ts`):**
   ```typescript
   // Example for Tamil Nadu (Madurai District)
   export const mockPHCs: PHC[] = [
     {
       id: 'phc-tn-1',
       name: 'Samayanallur Primary Health Centre',
       distance: 3.8,
       hours: '24/7',
       coordinates: [9.9821, 78.0412],
       doctorAvailable: true,
     },
     {
       id: 'phc-tn-2',
       name: 'Alanganallur Community Health Centre',
       distance: 14.2,
       hours: '24/7',
       coordinates: [10.0451, 78.0934],
       doctorAvailable: true,
     },
     {
       id: 'phc-tn-3',
       name: 'Thiruparankundram Urban PHC',
       distance: 7.1,
       hours: '8 AM - 4 PM',
       coordinates: [9.8824, 78.0719],
       doctorAvailable: false,
     }
   ];
   ```

### Step 2: Update Backend Database Seed Data

Edit `backend/scripts/seed_phc_data.py`:
```python
# Example for Jharkhand (Ranchi District)
PHCS = [
    dict(name="Kanke Community Health Centre", district="Ranchi", facility_type="CHC",
         phone="+91-651-2451201", latitude=23.4312, longitude=85.3214, is_24x7=True, doctor_available=True, hours="24/7"),
    dict(name="Namkum Primary Health Centre", district="Ranchi", facility_type="PHC",
         phone="+91-651-2260114", latitude=23.3321, longitude=85.3912, is_24x7=False, doctor_available=False, hours="9 AM - 5 PM"),
    dict(name="Ranchi Sadar Hospital", district="Ranchi", facility_type="District Hospital",
         phone="+91-651-2214400", latitude=23.3621, longitude=85.3256, is_24x7=True, doctor_available=True, hours="24/7"),
]

ASHA_WORKERS = [
    dict(asha_name="Birsi Munda", phone="+91-9876541101", village="Kanke", district="Ranchi"),
    dict(asha_name="Shanti Oraon", phone="+91-9876541102", village="Namkum", district="Ranchi"),
]
```

Re-seed the SQLite database:
```bash
rm swarasetu.db
python backend/scripts/seed_phc_data.py
```

### Step 3: Update Surveillance Dashboard District Names

Edit `src/data/mockDashboardData.ts`:
```typescript
// Example for Kerala
export const triageVolumeByDistrict = [
  { name: 'Wayanad', volume: 510 },
  { name: 'Palakkad', volume: 680 },
  { name: 'Malappuram', volume: 920 },
  { name: 'Idukki', volume: 430 },
  { name: 'Kozhikode', volume: 760 },
];
```

---

## 5. Automated ASHA Alert & Triage Routing Architecture

```
                      [ Patient Interaction ]
                 (Voice Recording / WhatsApp / ASHA Tablet)
                                  │
                                  ▼
                     [ WHO IMCI Clinical Engine ]
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                                         ▼
      [ Score 2: Yellow ]                       [ Score 3: Red ]
      (Moderate / Urgent)                       (Severe Emergency)
             │                                         │
             ▼                                         ▼
  [ Query AshaAssignment Table ]             [ Spatial Haversine Routing ]
             │                                         │
             ▼                                         ▼
[ Twilio SMS Dispatch to ASHA ]              [ Closest 24/7 PHC Identified ]
"🚨 ASHA ALERT: Moderate fever                         │
 reported in Belsand. Home visit                       ▼
 required within 24 hours."                 [ Emergency Card to Patient ]
                                            "📍 Nearest PHC: Belsand PHC
                                             📞 Emergency: +91-6226-282234
                                             Distance: ~4.2 km (Open: 24/7)"
```

---

## 6. Privacy & DPDP Act 2023 Compliance
- **Ephemeral Exact Location:** High-precision GPS fixes (`lat, lon` with 5 decimal places) are only used ephemerally to compute facility distance and are **never exposed on public dashboards**.
- **Aggregated District Telemetry:** District surveillance graphs aggregate data at the district/block level to protect patient confidentiality under India's Digital Personal Data Protection (DPDP) Act 2023.
