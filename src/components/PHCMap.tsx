import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { mockPHCs } from '@/data/mockPHCs';
import { Badge } from '@/components/ui/badge';
import { CloudOff, MapPin, Phone, Clock } from 'lucide-react';
import { api } from '@/lib/api';

// Fix for default Leaflet marker icons in React
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
});

function MapUpdater({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 11);
  }, [center, map]);
  return null;
}

interface MapFacility {
  id: string;
  name: string;
  distanceKm: number | null;
  hours: string;
  phone?: string;
  coordinates: [number, number];
  doctorAvailable: boolean;
}

const fallbackFacilities: MapFacility[] = mockPHCs.map((p) => ({
  id: p.id,
  name: p.name,
  distanceKm: p.distance,
  hours: p.hours,
  coordinates: p.coordinates,
  doctorAvailable: p.doctorAvailable,
}));

export function PHCMap() {
  const defaultCenter: [number, number] = [26.5, 85.5]; // Sitamarhi District coords
  const [facilities, setFacilities] = useState<MapFacility[]>(fallbackFacilities);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.nearestPhcs(defaultCenter[0], defaultCenter[1], 10);

        if (!cancelled && data.length > 0) {
          setFacilities(
            data.map((p) => ({
              id: String(p.id),
              name: p.name,
              distanceKm: p.distance_km,
              hours: p.hours,
              phone: p.phone,
              coordinates: [p.latitude, p.longitude],
              doctorAvailable: p.doctor_available,
            }))
          );
          setIsLive(true);
        }
      } catch {
        if (!cancelled) setIsLive(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="w-full flex flex-col h-full bg-[#f8fafc] rounded-2xl overflow-hidden font-sans">
      <div className="p-4 bg-white border-b border-slate-200 z-10 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-rose-600" />
          <h3 className="font-bold text-sm text-slate-900">
            Sitamarhi District — Nearest Primary Health Centers
          </h3>
        </div>
        {isLive ? (
          <Badge variant="outline" className="bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold text-xs">
            {facilities.length} PHCs Online
          </Badge>
        ) : (
          <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-800 flex items-center gap-1 text-xs font-semibold">
            <CloudOff className="w-3 h-3 text-amber-600" /> Cached PHCs (Offline)
          </Badge>
        )}
      </div>

      <div className="flex-1 w-full relative min-h-[400px]">
        <MapContainer center={defaultCenter} zoom={11} className="h-full w-full absolute inset-0 z-0">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapUpdater center={defaultCenter} />

          {facilities.map((phc) => (
            <Marker key={phc.id} position={phc.coordinates}>
              <Popup className="rounded-xl overflow-hidden shadow-lg border-0 p-0 m-0">
                <div className="min-w-[220px] p-2">
                  <h4 className="font-bold text-slate-900 text-sm mb-1 leading-tight">{phc.name}</h4>
                  <div className="flex items-center gap-1.5 my-2">
                    {phc.distanceKm !== null && (
                      <span className="text-[11px] font-bold bg-slate-100 text-slate-800 px-2 py-0.5 rounded-md">
                        {phc.distanceKm} km
                      </span>
                    )}
                    <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded-md flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {phc.hours}
                    </span>
                  </div>
                  {phc.phone && (
                    <a
                      href={`tel:${phc.phone}`}
                      className="flex items-center gap-1 text-[11px] font-bold text-[#0f4c42] hover:underline mb-2"
                    >
                      <Phone className="w-3 h-3" /> {phc.phone}
                    </a>
                  )}
                  <div
                    className={`text-[11px] font-bold px-2.5 py-1.5 rounded-md w-full text-center uppercase tracking-wider ${
                      phc.doctorAvailable
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {phc.doctorAvailable ? '✓ Doctor on Duty' : '⚠ Doctor Unavailable'}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
