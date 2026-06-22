from fastapi import APIRouter, HTTPException

from backend.services.address import AddressLookupError, lookup_cep


router = APIRouter(prefix="/api/address", tags=["Address"])


@router.get("/cep/{cep}")
def get_address_by_cep(cep: str):
    try:
        return lookup_cep(cep)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AddressLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
