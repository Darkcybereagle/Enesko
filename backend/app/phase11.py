from fastapi import APIRouter
router=APIRouter(prefix="/api/v1",tags=["Parking Integration"])
def seed_phase11(db): return
@router.get("/parking/integration-status")
def status():
    return {"adapter":"ParkingAdapter","configured":False,"health":"NOT_CONFIGURED","fallback":"staff_updated_phase10","live_counts_available":False}
