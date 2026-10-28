//! Per-match random stream (SIM_SPEC §1).
//!
//! One PCG32 stream per match, seeded with a fixed stream constant so a match is a
//! pure function of its `u64` seed. Floats are built from the top 24 bits of a
//! `u32` draw, which is exact in `f32` and identical on every target.

use crate::hash::{StateHash, StateHasher};

/// PCG stream selector shared by every match (SIM_SPEC §1).
pub const MATCH_STREAM: u64 = 0xda3e_39cb_94b9_5bdb;

/// `2^-24`: maps a 24-bit integer onto `[0, 1)` exactly.
const UNIT_24: f32 = 1.0 / 16_777_216.0;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Pcg32 {
    inner: rand_pcg::Pcg32,
}

impl Pcg32 {
    /// The stream a match with this seed uses.
    pub fn new(seed: u64) -> Self {
        Self::with_stream(seed, MATCH_STREAM)
    }

    /// Arbitrary stream; exists so tests can check against the PCG reference vectors.
    pub fn with_stream(seed: u64, stream: u64) -> Self {
        Pcg32 {
            inner: rand_pcg::Pcg32::new(seed, stream),
        }
    }

    #[inline]
    pub fn next_u32(&mut self) -> u32 {
        rand_core::Rng::next_u32(&mut self.inner)
    }

    /// Uniform in `[0, 1)`.
    #[inline]
    pub fn uniform(&mut self) -> f32 {
        (self.next_u32() >> 8) as f32 * UNIT_24
    }

    /// Uniform in `[lo, hi)` (for `lo < hi`).
    #[inline]
    pub fn range(&mut self, lo: f32, hi: f32) -> f32 {
        lo + (hi - lo) * self.uniform()
    }

    /// `(state, stream)`: the full generator state, for the state hash.
    pub fn state(&self) -> (u64, u64) {
        (self.inner.state(), self.inner.stream())
    }
}

impl StateHash for Pcg32 {
    fn hash_into(&self, h: &mut StateHasher) {
        let (state, stream) = self.state();
        h.write_u64(state);
        h.write_u64(stream);
    }
}

/// SplitMix64 finaliser: a bijective avalanche mix, so distinct inputs never collide.
#[inline]
fn mix64(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

/// Seed for match `index`, episode `episode` of a batch run from `base_seed`.
///
/// The VecEnv reseeds each auto-reset match with this, so episodes are
/// reproducible individually without replaying the batch. Chaining the mix keeps
/// `(index, episode)` pairs from aliasing the way `base + index + episode` would.
pub fn split(base_seed: u64, index: u64, episode: u64) -> u64 {
    const GAMMA: u64 = 0x9e37_79b9_7f4a_7c15;
    let h = mix64(base_seed.wrapping_add(GAMMA));
    let h = mix64(h ^ index.wrapping_add(GAMMA));
    mix64(h ^ episode.wrapping_add(GAMMA))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_pcg32_reference_vectors() {
        // pcg32-global-demo / pcg32_srandom_r(42, 54), from the PCG reference C code.
        let mut r = Pcg32::with_stream(42, 54);
        let got: Vec<u32> = (0..6).map(|_| r.next_u32()).collect();
        assert_eq!(
            got,
            [
                0xa15c02b7, 0x7b47f409, 0xba1d3330, 0x83d2f293, 0xbfa4784b, 0xcbed606e
            ]
        );
    }

    #[test]
    fn match_stream_golden_vector() {
        // Pins seed 7 on the match stream; any change here changes every match.
        let mut r = Pcg32::new(7);
        let ints: Vec<u32> = (0..4).map(|_| r.next_u32()).collect();
        let floats: Vec<u32> = (0..4).map(|_| r.uniform().to_bits()).collect();
        assert_eq!(ints, GOLDEN_SEED7_U32);
        assert_eq!(floats, GOLDEN_SEED7_UNIFORM_BITS);
    }

    const GOLDEN_SEED7_U32: [u32; 4] = [0xd2ccce99, 0x44d62f41, 0xad048b08, 0x56030b66];
    const GOLDEN_SEED7_UNIFORM_BITS: [u32; 4] = [0x3f51766d, 0x3da4ca70, 0x3edbe298, 0x3f197ea5];

    #[test]
    fn uniform_is_in_unit_interval_and_range_scales() {
        let mut r = Pcg32::new(1);
        for _ in 0..10_000 {
            let u = r.uniform();
            assert!((0.0..1.0).contains(&u));
            let x = r.range(-15.0, 15.0);
            assert!((-15.0..15.0).contains(&x));
        }
    }

    #[test]
    fn uniform_extremes_are_exact() {
        assert_eq!((0u32 >> 8) as f32 * UNIT_24, 0.0);
        assert!((u32::MAX >> 8) as f32 * UNIT_24 < 1.0);
    }

    #[test]
    fn same_seed_same_stream_and_state_roundtrips() {
        let mut a = Pcg32::new(99);
        let mut b = Pcg32::new(99);
        for _ in 0..100 {
            assert_eq!(a.next_u32(), b.next_u32());
        }
        assert_eq!(a.state(), b.state());
        assert_eq!(a.state().1, MATCH_STREAM & (u64::MAX >> 1));
        assert_ne!(Pcg32::new(1).next_u32(), Pcg32::new(2).next_u32());
    }

    #[test]
    fn split_separates_matches_and_episodes() {
        let mut seen = std::collections::BTreeSet::new();
        for i in 0..64 {
            for k in 0..64 {
                assert!(seen.insert(split(5, i, k)), "collision at ({i}, {k})");
            }
        }
        assert_eq!(split(5, 3, 4), split(5, 3, 4));
        assert_ne!(split(5, 3, 4), split(6, 3, 4));
        assert_ne!(split(5, 3, 4), split(5, 4, 3));
    }
}
