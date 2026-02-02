"""
Cliente para la API de Stats Perform (SDAPI - performfeeds).
"""
from __future__ import annotations
import os
import time
import hashlib
from typing import Any, Dict, Optional, Union
import requests


class StatsPerformClient:
    """
    Cliente básico para SDAPI (performfeeds) de Stats Perform con soporte OAuth.
    """
    
    def __init__(
        self,
        outlet_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = "https://api.performfeeds.com",
        oauth_url: str = "https://oauth.performgroup.com/oauth/token",
        sport: str = "soccer",
        timeout: int = 30,
        max_retries: int = 5,
        backoff_seconds: float = 2.0,
        default_params: Optional[Dict[str, Any]] = None,
        use_oauth: bool = True,
    ):
        """
        Inicializa el cliente de Stats Perform.
        
        Args:
            outlet_key: Clave de autenticación (outlet key). Si no se proporciona, 
                       se toma de la variable de entorno SDAPI_OUTLET_KEY.
            secret_key: Clave secreta para OAuth. Si no se proporciona,
                       se toma de la variable de entorno SDAPI_SECRET_KEY.
            base_url: URL base de la API.
            oauth_url: URL base del servidor OAuth.
            sport: Deporte (por defecto "soccer").
            timeout: Tiempo máximo de espera para las peticiones (segundos).
            max_retries: Número máximo de reintentos en caso de error (default: 5).
            backoff_seconds: Tiempo inicial de espera entre reintentos (segundos, default: 2.0).
            default_params: Parámetros por defecto para todas las peticiones.
            use_oauth: Si True, usa autenticación OAuth. Si False, usa método tradicional.
        """
        self.outlet_key = outlet_key or os.getenv("SDAPI_OUTLET_KEY", "czumn6sja9291tylsewlnuyl0")
        self.secret_key = secret_key or os.getenv("SDAPI_SECRET_KEY", "jol3ie4f5ies1kcxo2q9xro3g")
        self.base_url = base_url.rstrip("/")
        self.oauth_url = oauth_url.rstrip("/")
        self.sport = sport.strip().lower()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.default_params = default_params or {}
        self.use_oauth = use_oauth
        
        # OAuth token management
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Racing-Santander-DS/1.0",
            "Accept": "application/json, application/xml;q=0.9, */*;q=0.8",
        })

    def _generate_hash(self) -> tuple[str, int]:
        """
        Genera el hash SHA512 para autenticación OAuth.
        
        Returns:
            Tupla con (hash, timestamp)
        """
        timestamp = int(time.time() * 1000)
        hash_string = f"{self.outlet_key}{timestamp}{self.secret_key}"
        hash_value = hashlib.sha512(hash_string.encode()).hexdigest()
        return hash_value, timestamp
    
    def _get_oauth_token(self) -> str:
        """
        Obtiene un token OAuth válido (reutiliza si no ha expirado) con reintentos.
        
        Returns:
            Token de acceso OAuth
        """
        # Verificar si tenemos un token válido
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        
        # Intentar obtener nuevo token con reintentos
        max_token_retries = 3
        for attempt in range(1, max_token_retries + 1):
            try:
                # Generar nuevo token
                hash_value, timestamp = self._generate_hash()
                
                url = f"{self.oauth_url}/{self.outlet_key}"
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {hash_value}",
                    "Timestamp": str(timestamp)
                }
                data = {
                    "grant_type": "client_credentials",
                    "scope": "b2b-feeds-auth"
                }
                
                resp = requests.post(url, headers=headers, data=data, params={"_fmt": "json", "_rt": "b"}, timeout=10)
                resp.raise_for_status()
                
                token_data = resp.json()
                self._access_token = token_data["access_token"]
                # Guardar tiempo de expiración (60 segundos menos 5 segundos de margen)
                self._token_expiry = time.time() + 55
                
                if attempt > 1:
                    print(f"✓ Token OAuth obtenido después de {attempt} intentos")
                
                return self._access_token
                
            except Exception as e:
                if attempt == max_token_retries:
                    print(f"✗ Error obteniendo token OAuth después de {max_token_retries} intentos: {e}")
                    raise
                
                print(f"⚠ Intento {attempt}/{max_token_retries} de obtener token falló: {e}")
                time.sleep(2 * attempt)  # Backoff simple
        
        raise RuntimeError("No se pudo obtener token OAuth")
    
    def _prepare_request_headers(self) -> Dict[str, str]:
        """
        Prepara los headers para la petición según el método de autenticación.
        
        Returns:
            Diccionario con headers adicionales
        """
        if self.use_oauth:
            token = self._get_oauth_token()
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Realiza una petición HTTP con reintentos automáticos y backoff exponencial.
        
        Args:
            method: Método HTTP (GET, POST, etc.).
            url: URL completa de la petición.
            **kwargs: Argumentos adicionales para requests.
            
        Returns:
            Respuesta de la petición.
            
        Raises:
            requests.HTTPError: Si la petición falla después de todos los reintentos.
        """
        # Añadir headers de autenticación si se usa OAuth
        headers = kwargs.get('headers', {})
        if self.use_oauth:
            headers.update(self._prepare_request_headers())
        kwargs['headers'] = headers
        
        last_exc = None
        delay = self.backoff_seconds
        
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                
                # Verificar códigos de error del servidor
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"{resp.status_code} server error", response=resp)
                
                # Si llegamos aquí, la petición fue exitosa
                if attempt > 1:
                    # Log solo si hubo reintentos
                    print(f"✓ Petición exitosa después de {attempt} intentos")
                
                return resp
                
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                last_exc = e
                
                if attempt == self.max_retries:
                    print(f"✗ Petición falló después de {self.max_retries} intentos: {e}")
                    raise
                
                # Log del error y espera
                print(f"⚠ Intento {attempt}/{self.max_retries} falló: {e}")
                print(f"  Reintentando en {delay:.1f}s...")
                time.sleep(delay)
                
                # Backoff exponencial con límite máximo
                delay = min(delay * 2, 60)  # Máximo 60 segundos
        
        assert last_exc is not None
        raise last_exc

    def _parse(self, resp: requests.Response) -> Union[Dict[str, Any], str]:
        """
        Parsea la respuesta según su tipo de contenido.
        
        Args:
            resp: Respuesta de la petición.
            
        Returns:
            Diccionario si es JSON, string si es XML u otro formato.
        """
        ctype = resp.headers.get("Content-Type", "")
        if "json" in ctype.lower():
            return resp.json()
        return resp.text

    def _make_url(self, *parts: str) -> str:
        """
        Construye una URL a partir de varias partes.
        
        Args:
            *parts: Partes de la URL.
            
        Returns:
            URL completa.
        """
        all_parts = [self.base_url] + [p.strip("/") for p in parts]
        return "/".join(all_parts)

    def get_match_detailed(
        self,
        competition_ids: Union[str, list[str]],
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene los detalles de partidos para una o más competiciones (feed matchdetailed).
        
        Args:
            competition_ids: ID(s) de la(s) competición(es). Puede ser un string único 
                           o una lista de strings que se unirán con comas.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de los partidos o string XML.
            
        Ejemplo:
            >>> client = StatsPerformClient()
            >>> # Una sola competición
            >>> data = client.get_match_detailed("dko0hzifl1xv9c51s3ai017v8")
            >>> # Múltiples competiciones
            >>> data = client.get_match_detailed(["comp1", "comp2"])
        """
        url = self._make_url(f"{self.sport}data", "matchdetailed", self.outlet_key)
        
        params = dict(self.default_params)
        
        # Manejar múltiples competiciones
        if isinstance(competition_ids, list):
            params["comp"] = ",".join(competition_ids)
        else:
            params["comp"] = competition_ids
            
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "json")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_match_stats(
        self,
        status: str = "played",
        date_filter: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene estadísticas de partidos (feed matchstats).
        
        Args:
            status: Estado de los partidos ('played', 'fixture', 'all', etc.).
            date_filter: Filtro de fecha para limitar resultados.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de estadísticas o string XML.
            
        Ejemplo:
            >>> client = StatsPerformClient()
            >>> # Obtener partidos jugados
            >>> data = client.get_match_stats(status="played")
            >>> # Con filtro de fecha
            >>> data = client.get_match_stats(status="played", date_filter="dateTime")
        """
        url = self._make_url(f"{self.sport}data", "matchstats", self.outlet_key)
        
        params = dict(self.default_params)
        params["status"] = status
        
        if date_filter:
            params["_dlt"] = date_filter
            
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "json")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_match_stats_by_id(
        self,
        match_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene estadísticas detalladas de un partido específico (feed matchstats con fx).
        
        Args:
            match_id: ID del partido.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de estadísticas del partido o string XML.
            
        Ejemplo:
            >>> client = StatsPerformClient()
            >>> data = client.get_match_stats_by_id("3oltaoszee44cjqdl75mspams")
        """
        url = self._make_url(f"{self.sport}data", "matchstats", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "json")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_tournament_calendar(
        self,
        authorized: bool = True,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene los calendarios de torneos (tmcl).
        IMPORTANTE: Sin filtro de status retorna TODAS las temporadas (activas e inactivas).
        
        Args:
            authorized: Si se filtran solo torneos autorizados.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de los torneos o string XML.
        """
        path_parts = [
            f"{self.sport}data",
            "tournamentcalendar",
            self.outlet_key
        ]
        if authorized:
            path_parts.append("authorized")
        url = self._make_url(*path_parts)

        params = dict(self.default_params)
        if extra_params:
            params.update(extra_params)
        params.setdefault("_fmt", "json")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_tournament_schedule(
        self,
        tmcl_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene el calendario de partidos para un torneo (feed MA0).
        
        Args:
            tmcl_id: ID del torneo (tournament calendar ID).
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de los partidos o string XML.
        """
        url = self._make_url(f"{self.sport}data", "tournamentschedule", self.outlet_key)
        
        params = dict(self.default_params)
        params["tmcl"] = tmcl_id
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_match_events(
        self,
        match_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene los eventos de un partido (feed MA3).
        
        Args:
            match_id: ID del partido.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de eventos o string XML.
        """
        url = self._make_url(f"{self.sport}data", "matchevent", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_decode_data(
        self,
        entity_type: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene datos de decodificación para un tipo de entidad (feed DE1).
        
        Args:
            entity_type: Tipo de entidad ("Qualifier", "Eventtype", "teamFormationDetailed", etc.).
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de decodificación o string XML.
        """
        url = self._make_url(f"{self.sport}data", "decode", self.outlet_key)
        
        params = dict(self.default_params)
        params["type"] = entity_type
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_squad(
        self,
        tmcl_id: str,
        detailed: bool = True,
        format: str = "json",
        extra_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene la plantilla (squad) de un torneo/competición.
        Maneja paginación automáticamente para obtener todos los equipos.
        
        Args:
            tmcl_id: ID del torneo (tournament calendar ID).
            detailed: Si True, devuelve información detallada de jugadores.
            format: Formato de respuesta ('json' o 'xml').
            extra_params: Parámetros adicionales para la petición.
            page_size: Tamaño de página para paginación (default 100).
            
        Returns:
            Diccionario con los datos de la plantilla (si format='json') o string XML (si format='xml').
        """
        url = self._make_url(f"{self.sport}data", "squads", self.outlet_key)
        
        params = dict(self.default_params)
        params["tmcl"] = tmcl_id
        params["detailed"] = "yes" if detailed else "no"
        params["_fmt"] = format
        params["_rt"] = "b"
        params["_pgSz"] = page_size  # Page size
        params["_pgNm"] = 1  # Start from page 1
        
        if extra_params:
            params.update(extra_params)

        resp = self._request("GET", url, params=params)
        
        # Si el formato es JSON, parsear como JSON directamente
        if format == "json" and resp:
            data = resp.json()
            
            # Si hay múltiples páginas, obtener todas
            if 'squad' in data:
                all_squads = data['squad'] if isinstance(data['squad'], list) else [data['squad']]
                
                # Verificar si hay más páginas
                page_number = 1
                while len(all_squads) == page_size * page_number:
                    page_number += 1
                    params["_pgNm"] = page_number
                    
                    resp_next = self._request("GET", url, params=params)
                    data_next = resp_next.json()
                    
                    if 'squad' in data_next and data_next['squad']:
                        next_squads = data_next['squad'] if isinstance(data_next['squad'], list) else [data_next['squad']]
                        all_squads.extend(next_squads)
                    else:
                        break
                
                data['squad'] = all_squads
            
            return data
        
        return self._parse(resp)

    def get_player_contracts(
        self,
        contestant_id: str,
        format: str = "json",
        extra_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene información de contratos de jugadores de un equipo.
        Maneja paginación automáticamente para obtener todos los contratos.
        
        Args:
            contestant_id: ID del equipo/contestant.
            format: Formato de respuesta ('json' o 'xml').
            extra_params: Parámetros adicionales para la petición.
            page_size: Tamaño de página para paginación (default 100).
            
        Returns:
            Diccionario con los datos de contratos (si format='json') o string XML (si format='xml').
        """
        url = self._make_url(f"{self.sport}data", "playercontract", self.outlet_key)
        
        params = dict(self.default_params)
        params["ctst"] = contestant_id
        params["_fmt"] = format
        params["_rt"] = "b"
        params["_pgSz"] = page_size
        params["_pgNm"] = 1
        
        if extra_params:
            params.update(extra_params)

        resp = self._request("GET", url, params=params)
        
        # Si el formato es JSON, parsear como JSON directamente
        if format == "json" and resp:
            data = resp.json()
            
            # Si hay múltiples páginas, obtener todas
            if 'person' in data:
                all_persons = data['person'] if isinstance(data['person'], list) else [data['person']]
                
                # Verificar si hay más páginas
                page_number = 1
                while len(all_persons) == page_size * page_number:
                    page_number += 1
                    params["_pgNm"] = page_number
                    
                    resp_next = self._request("GET", url, params=params)
                    data_next = resp_next.json()
                    
                    if 'person' in data_next and data_next['person']:
                        next_persons = data_next['person'] if isinstance(data_next['person'], list) else [data_next['person']]
                        all_persons.extend(next_persons)
                    else:
                        break
                
                data['person'] = all_persons
            
            return data
        
        return self._parse(resp)

    def get_season_stats(
        self,
        tournament_id: str,
        contestant_id: str,
        detailed: bool = True,
        format: str = "json",
        extra_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Union[Dict[str, Any], Any]:
        """
        Obtiene estadísticas de temporada para un equipo específico.
        Maneja paginación automáticamente para obtener todos los jugadores.
        
        Args:
            tournament_id: ID del torneo/temporada (tmcl parameter)
            contestant_id: ID del equipo (ctst parameter)
            detailed: Si True, obtiene estadísticas detalladas
            format: Formato de respuesta ('json' o 'xml')
            extra_params: Parámetros adicionales para la consulta
            page_size: Tamaño de página para paginación (default 100)
            
        Returns:
            Diccionario con estadísticas si format='json', sino la respuesta parseada
        """
        # Construir URL
        url = self._make_url(f"{self.sport}data", "seasonstats", self.outlet_key)
        
        # Parámetros base
        params = dict(self.default_params)
        params["tmcl"] = tournament_id
        params["ctst"] = contestant_id
        params["detailed"] = "yes" if detailed else "no"
        params["_fmt"] = format
        params["_rt"] = "b"
        params["_pgSz"] = page_size
        params["_pgNm"] = 1
        
        # Agregar parámetros extra si existen
        if extra_params:
            params.update(extra_params)
        
        # Hacer la solicitud
        resp = self._request("GET", url, params=params)
        
        # Si el formato es JSON, parsear como JSON directamente
        if format == "json" and resp:
            data = resp.json()
            
            # Si hay múltiples páginas, obtener todas
            if 'player' in data:
                all_players = data['player'] if isinstance(data['player'], list) else [data['player']]
                
                # Verificar si hay más páginas
                page_number = 1
                while len(all_players) == page_size * page_number:
                    page_number += 1
                    params["_pgNm"] = page_number
                    
                    resp_next = self._request("GET", url, params=params)
                    data_next = resp_next.json()
                    
                    if 'player' in data_next and data_next['player']:
                        next_players = data_next['player'] if isinstance(data_next['player'], list) else [data_next['player']]
                        all_players.extend(next_players)
                    else:
                        break
                
                data['player'] = all_players
            
            return data
        
        return self._parse(resp)

    def get_match_possession_values(
        self,
        match_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene los valores de posesión de un partido (feed MA30).
        
        Args:
            match_id: ID del partido.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de posesión o string XML.
        """
        url = self._make_url(f"{self.sport}data", "matcheventspossessionvalues", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_remote_events(
        self,
        match_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Obtiene eventos enriched con datos de tracking (remoteevents).
        
        Args:
            match_id: ID del partido.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con eventos enriched (ya parseado).
        """
        url = self._make_url(f"{self.sport}data", "remoteevents", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "json")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        # _parse() ya devuelve un dict cuando content-type es JSON
        return self._parse(resp)

    def get_remote_match_tracking_metadata(
        self,
        match_id: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Obtiene metadata de tracking EPTS (contiene URL del archivo de tracking).
        
        Args:
            match_id: ID del partido.
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            String XML con metadata (incluye URL del archivo .txt de tracking).
        """
        url = self._make_url(f"{self.sport}data", "remotematchtrackingepts", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)

    def get_remote_aggregated_fitness(
        self,
        match_id: str,
        fitness_type: str = "fifa",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Obtiene datos de fitness agregados de un partido (remoteaggregatedfitness).
        
        Args:
            match_id: ID del partido.
            fitness_type: Tipo de datos de fitness (por defecto "fifa").
            extra_params: Parámetros adicionales para la petición.
            
        Returns:
            Diccionario con los datos de fitness o string XML.
        """
        url = self._make_url(f"{self.sport}data", "remoteaggregatedfitness", self.outlet_key)
        
        params = dict(self.default_params)
        params["fx"] = match_id
        params["type"] = fitness_type
        if extra_params:
            params.update(extra_params)
        
        params.setdefault("_fmt", "xml")
        params.setdefault("_rt", "b")

        resp = self._request("GET", url, params=params)
        return self._parse(resp)
