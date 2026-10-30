
export type TourApi = {
  tou_id_tou: number;
  tou_nom_tou: string;
  tou_des_tou: string | null;
  tou_dur_hor: number | null;
  tou_dur_dia: number | null;
  tou_cup_max: number;
};

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export async function obtenerToursActivos(): Promise<TourApi[]> {
  const response = await fetch(`${API_BASE_URL}/tours/`);

  if (!response.ok) {
    throw new Error(
      `Error consultando tours en Django: ${response.status}`,
    );
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error(
      'La API de tours no devolvió una lista válida.',
    );
  }

  return data as TourApi[];
}

export async function obtenerTourPorId(
  id: number,
): Promise<TourApi | null> {
  const response = await fetch(`${API_BASE_URL}/tours/${id}/`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      `Error consultando el tour ${id} en Django: ${response.status}`,
    );
  }

  return (await response.json()) as TourApi;
}
