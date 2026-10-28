//! FNV-1a 64 state hashing for the determinism contract (SIM_SPEC §12).
//!
//! Implemented here rather than via `std::hash` because `Hasher` output is not
//! guaranteed stable across Rust versions or targets, and the golden traces must
//! match between native and wasm32 forever. Floats hash by bit pattern so `-0.0`,
//! `0.0` and distinct NaNs all count as different state. Multi-byte values are fed
//! little-endian and `usize` is widened to `u64`, so 32-bit wasm and 64-bit native
//! hash identically.

use crate::math::Vec2;

const FNV_OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const FNV_PRIME: u64 = 0x0000_0100_0000_01b3;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StateHasher {
    h: u64,
}

impl Default for StateHasher {
    fn default() -> Self {
        Self::new()
    }
}

impl StateHasher {
    pub fn new() -> Self {
        StateHasher { h: FNV_OFFSET }
    }

    #[inline]
    pub fn write_bytes(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.h ^= u64::from(b);
            self.h = self.h.wrapping_mul(FNV_PRIME);
        }
    }

    #[inline]
    pub fn write_u8(&mut self, v: u8) {
        self.write_bytes(&[v]);
    }

    #[inline]
    pub fn write_i8(&mut self, v: i8) {
        self.write_bytes(&v.to_le_bytes());
    }

    #[inline]
    pub fn write_bool(&mut self, v: bool) {
        self.write_u8(u8::from(v));
    }

    #[inline]
    pub fn write_u16(&mut self, v: u16) {
        self.write_bytes(&v.to_le_bytes());
    }

    #[inline]
    pub fn write_u32(&mut self, v: u32) {
        self.write_bytes(&v.to_le_bytes());
    }

    #[inline]
    pub fn write_i32(&mut self, v: i32) {
        self.write_bytes(&v.to_le_bytes());
    }

    #[inline]
    pub fn write_u64(&mut self, v: u64) {
        self.write_bytes(&v.to_le_bytes());
    }

    /// Widened to `u64` so the hash does not depend on pointer width.
    #[inline]
    pub fn write_usize(&mut self, v: usize) {
        self.write_u64(v as u64);
    }

    #[inline]
    pub fn write_f32(&mut self, v: f32) {
        self.write_u32(v.to_bits());
    }

    #[inline]
    pub fn write_vec2(&mut self, v: Vec2) {
        self.write_f32(v.x);
        self.write_f32(v.y);
    }

    pub fn finish(&self) -> u64 {
        self.h
    }
}

/// Types that feed themselves into a [`StateHasher`] in a fixed field order.
/// State structs implement this so `Match::state_hash` stays a flat walk.
pub trait StateHash {
    fn hash_into(&self, h: &mut StateHasher);
}

macro_rules! impl_state_hash {
    ($($t:ty => $m:ident),* $(,)?) => {
        $(impl StateHash for $t {
            #[inline]
            fn hash_into(&self, h: &mut StateHasher) {
                h.$m(*self);
            }
        })*
    };
}

impl_state_hash!(
    u8 => write_u8, i8 => write_i8, bool => write_bool, u16 => write_u16,
    u32 => write_u32, i32 => write_i32, u64 => write_u64, usize => write_usize,
    f32 => write_f32, Vec2 => write_vec2,
);

impl<T: StateHash, const N: usize> StateHash for [T; N] {
    fn hash_into(&self, h: &mut StateHasher) {
        for v in self {
            v.hash_into(h);
        }
    }
}

impl<T: StateHash> StateHash for [T] {
    fn hash_into(&self, h: &mut StateHasher) {
        for v in self {
            v.hash_into(h);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fnv(bytes: &[u8]) -> u64 {
        let mut h = StateHasher::new();
        h.write_bytes(bytes);
        h.finish()
    }

    #[test]
    fn matches_published_fnv1a_64_vectors() {
        assert_eq!(fnv(b""), 0xcbf29ce484222325);
        assert_eq!(fnv(b"a"), 0xaf63dc4c8601ec8c);
        assert_eq!(fnv(b"foobar"), 0x85944171f73967e8);
    }

    #[test]
    fn integers_hash_little_endian() {
        let mut a = StateHasher::new();
        a.write_u32(0x0403_0201);
        assert_eq!(a.finish(), fnv(&[1, 2, 3, 4]));

        let mut b = StateHasher::new();
        b.write_usize(7);
        let mut c = StateHasher::new();
        c.write_u64(7);
        assert_eq!(b.finish(), c.finish());
    }

    #[test]
    fn floats_hash_by_bit_pattern() {
        let hash = |v: f32| {
            let mut h = StateHasher::new();
            h.write_f32(v);
            h.finish()
        };
        assert_ne!(hash(0.0), hash(-0.0));
        assert_eq!(hash(1.5), fnv(&1.5f32.to_bits().to_le_bytes()));
    }

    #[test]
    fn order_matters() {
        let mut a = StateHasher::new();
        a.write_vec2(Vec2::new(1.0, 2.0));
        let mut b = StateHasher::new();
        b.write_vec2(Vec2::new(2.0, 1.0));
        assert_ne!(a.finish(), b.finish());
    }

    #[test]
    fn trait_matches_direct_writes() {
        let mut a = StateHasher::new();
        [1u8, 2, 3].hash_into(&mut a);
        true.hash_into(&mut a);
        Vec2::new(0.5, -0.5).hash_into(&mut a);
        let mut b = StateHasher::new();
        b.write_bytes(&[1, 2, 3, 1]);
        b.write_f32(0.5);
        b.write_f32(-0.5);
        assert_eq!(a.finish(), b.finish());
    }
}
