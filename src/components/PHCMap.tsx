import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { mockPHCs } from '@/data/mockPHCs';
import { Badge } from '@/components/ui/badge';
import { CloudOff } from 'lucide-react';
import type { PHCNearby } from '@/types/api';

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

/** Static fixtures rendered as fallback when the backend is unreachable. */
const fallbackFacilities: MapFacility[] = mockPHCs.map((p) => ({
  id: p.id,
  name: p.name,
  distanceKm: p.distance,
  hours: p.hours,
  coordinates: p.coordinates,
  doctorAvailable: p.doctorAvailable,
}));

export function PHCMap() {
  const defaultCenter: [number, number] = [26.5, 85.5]; // Central Rural Bihar coords
  const [facilities, setFacilities] = useState<MapFacility[]>(fallbackFacilities);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`/api/v1/phcs/nearest?lat=${defaultCenter[0]}&lon=${defaultCenter[1]}&limit=10`);
        if (!res.ok) throw new Error(String(res.status));
        const data = (await res.json()) as PHCNearby[];
        if (cancelled || data.length === 0) return;
        setFacilities(
          data.map((p) => ({
            id: String(p.id),
            name: p.name,
            distanceKm: p.distance_km,
            hours: p.hours,
            phone: p.phone,
            coordinates: [p.latitude, p.longitude] as [number, number],
            doctorAvailable: p.doctor_available,
          })),
        );
        setIsLive(true);
      } catch {
        if (!cancelled) setIsLive(false); // keep static fallback pins
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="w-full flex flex-col h-full bg-slate-50 dark:bg-slate-900 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm relative z-0">
      <div className="p-4 bg-white dark:bg-slate-950 border-b border-slate-100 dark:border-slate-800 z-10 flex justify-between items-center">
        <h3 className="font-semibold text-slate-800 dark:text-slate-100">Nearest Primary Health Centers</h3>
        {isLive ? (
          <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-400 shadow-none">
            {facilities.length} Available
          </Badge>
        ) : (
          <Badge variant="outline" className="border-amber-300 text-amber-700 dark:text-amber-400 flex items-center gap-1">
            <CloudOff className="w-3 h-3" /> Cached Pins
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

          {facilities.map(_phc => (
            <Marker key={_phc.id} position={_phc.coordinates}>
              <Popup className="rounded-xl overflow-hidden shadow-lg border-0 p-0 m-0">
                <div className="min-w-[200px] pb-1">
                  <h4 className="font-bold text-slate-800 text-[15px] mb-1 leading-tight">{_phc.name}</h4>
                  <div className="flex items-center gap-1.5 mb-2 mt-2">
                    {_phc.distanceKm !== null && (
                      <span className="text-[11px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-sm">{_phc.distanceKm} km</span>
                    )}
                    <span className="text-[11px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-sm">{_phc.hours}</span>
                  </div>
                  {_phc.phone && (
                    <a href={`tel:${_phc.phone}`} className="block text-[11px] font-semibold text-blue-600 hover:underline mb-2">
                      {_phc.phone}
                    </a>
                  )}
                  <div className={`text-[11px] font-bold px-2 py-1.5 rounded w-full text-center uppercase tracking-wider ${
                    _phc.doctorAvailable
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}>
                    {_phc.doctorAvailable ? 'Doctor Available' : 'Doctor Unavailable'}
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
