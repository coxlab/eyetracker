
# ==============================================
# Cameras
# ==============================================

from POVRaySimulatedCameraDevice import *
from FakeCameraDevice import *

try:
	from ProsilicaCameraDevice import *
except e:
	pass

# ==============================================
# LED Controllers
# ==============================================

from SimulatedLEDController import *
from MightexLEDController import *

# ==============================================
# Stage (Motion) Controllers
# ==============================================

from SimulatedStageController import *
from EyeTrackerStageController import *
from ESP300StageController import *
from FocusAndZoomController import *

# ==============================================
# Feature Finders (i.e. image processing)
# ==============================================

## Choose the starburst algorithm
#FlagStarBurstAlgorithm = 2
#if FlagStarBurstAlgorithm == 1:
#    # Starburst only feature finder (5 cycles of rays chooted)    
#    from StarBurstEyeFeatureFinder import *
#elif FlagStarBurstAlgorithm == 2:
#    # Starburst + circle fit feature finder (1 cycles of rays chooted + 1 least squares fit with circle)    
#    from StarBurstCircleLstsqFitEyeFeatureFinder import *

#from StarBurstCircleLstsqFitEyeFeatureFinder import *
from FastRadialFeatureFinder import *
from PipelinedFeatureFinder import *
from CompositeEyeFeatureFinder import *
from FrugalCompositeEyeFeatureFinder import *
from SimpleEyeFeatureFinder import *


# ==============================================
# Calibrators
# ==============================================

from StahlLikeCalibrator import *
