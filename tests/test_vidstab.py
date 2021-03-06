import tempfile
import cv2
import imutils
import numpy as np
import pytest

from vidstab import VidStab
from vidstab.download_videos import download_ostrich_video, download_truncated_ostrich_video
from .pickled_transforms import download_pickled_transforms, pickle_test_transforms

# atol value to use when comparing results using np.allclose
NP_ALLCLOSE_ATOL = 1e-3

# excluding non-free "SIFT" & "SURF" methods do to exclusion from opencv-contrib-python
# see: https://github.com/skvark/opencv-python/issues/126
KP_METHODS = ["GFTT", "BRISK", "DENSE", "FAST", "HARRIS", "MSER", "ORB", "STAR"]

tmp_dir = tempfile.TemporaryDirectory()
TRUNCATED_OSTRICH_VIDEO = '{}/trunc_vid.avi'.format(tmp_dir.name)
OSTRICH_VIDEO = '{}/vid.avi'.format(tmp_dir.name)

download_truncated_ostrich_video(TRUNCATED_OSTRICH_VIDEO)
download_ostrich_video(OSTRICH_VIDEO)


# test that all keypoint detection methods load without error
def test_default_init():
    for kp in KP_METHODS:
        print('testing kp method {}'.format(kp))
        assert VidStab(kp_method=kp).kp_method == kp


def test_kp_options():
    stabilizer = VidStab(kp_method='FAST', threshold=42, nonmaxSuppression=False)
    assert not stabilizer.kp_detector.getNonmaxSuppression()
    assert stabilizer.kp_detector.getThreshold() == 42

    with pytest.raises(TypeError) as err:
        VidStab(kp_method='FAST', fake='fake')

    assert 'invalid keyword argument' in str(err.value)


def test_invalid_input_path():
    stabilizer = VidStab(kp_method='FAST', threshold=42, nonmaxSuppression=False)
    with pytest.raises(FileNotFoundError) as err:
        stabilizer.gen_transforms("fake_input_path.mp4")

    assert "fake_input_path.mp4 does not exist" in str(err.value)

    with pytest.raises(FileNotFoundError) as err:
        stabilizer.stabilize("fake_input_path.mp4", "output.avi")

    assert "fake_input_path.mp4 does not exist" in str(err.value)


def test_video_dep_funcs_run():
    # just tests to check functions run
    stabilizer = VidStab()
    stabilizer.gen_transforms(TRUNCATED_OSTRICH_VIDEO, smoothing_window=2, show_progress=True)

    assert stabilizer.smoothed_trajectory.shape == stabilizer.trajectory.shape
    assert stabilizer.transforms.shape == stabilizer.trajectory.shape

    with tempfile.TemporaryDirectory() as tmpdir:
        output_vid = '{}/test_output.avi'.format(tmpdir)
        stabilizer.apply_transforms(TRUNCATED_OSTRICH_VIDEO, output_vid)
        stabilizer.stabilize(TRUNCATED_OSTRICH_VIDEO, output_vid, smoothing_window=2)


def check_transforms(stabilizer, is_cv4=True):
    # noinspection PyProtectedMember
    unpickled_transforms = download_pickled_transforms(stabilizer._smoothing_window, cv4=is_cv4)

    assert np.allclose(stabilizer.transforms, unpickled_transforms[0], atol=NP_ALLCLOSE_ATOL)
    assert np.allclose(stabilizer.trajectory, unpickled_transforms[1], atol=NP_ALLCLOSE_ATOL)
    assert np.allclose(stabilizer.smoothed_trajectory, unpickled_transforms[2], atol=NP_ALLCLOSE_ATOL)


def test_trajectory_transform_values():
    for window in [15, 30, 60]:
        stabilizer = VidStab()
        stabilizer.gen_transforms(input_path=OSTRICH_VIDEO, smoothing_window=window)

        pickle_test_transforms(stabilizer, 'pickled_transforms')

        check_transforms(stabilizer, is_cv4=imutils.is_cv4())


def test_stabilize_frame():
    # Init stabilizer and video reader
    stabilizer = VidStab()
    vidcap = cv2.VideoCapture(OSTRICH_VIDEO)

    window_size = 30
    while True:
        grabbed_frame, frame = vidcap.read()

        # Pass frame to stabilizer even if frame is None
        stabilized_frame = stabilizer.stabilize_frame(input_frame=frame,
                                                      smoothing_window=window_size,
                                                      border_size=10)

        if stabilized_frame is None:
            break

    check_transforms(stabilizer, is_cv4=imutils.is_cv4())


if __name__ == '__main__':
    test_trajectory_transform_values()
    test_stabilize_frame()
