//! 2D vector maths for the sim.
//!
//! Determinism: every transcendental goes through `libm` (pure Rust, identical on
//! native and wasm32) rather than `f32::sin` and friends, whose results depend on the
//! platform's libm. Nothing here uses `mul_add`, so the compiler never fuses
//! operations differently per target.

use core::ops::{Add, AddAssign, Div, Mul, MulAssign, Neg, Sub, SubAssign};

pub const PI: f32 = core::f32::consts::PI;
pub const TAU: f32 = core::f32::consts::TAU;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Vec2 {
    pub x: f32,
    pub y: f32,
}

impl Vec2 {
    pub const ZERO: Vec2 = Vec2 { x: 0.0, y: 0.0 };
    pub const X: Vec2 = Vec2 { x: 1.0, y: 0.0 };
    pub const Y: Vec2 = Vec2 { x: 0.0, y: 1.0 };

    #[inline]
    pub const fn new(x: f32, y: f32) -> Self {
        Vec2 { x, y }
    }

    /// Unit vector at angle `theta` (CCW from +x).
    #[inline]
    pub fn from_angle(theta: f32) -> Self {
        Vec2::new(libm::cosf(theta), libm::sinf(theta))
    }

    #[inline]
    pub fn dot(self, o: Vec2) -> f32 {
        self.x * o.x + self.y * o.y
    }

    /// z component of the 3D cross product; positive when `o` is CCW of `self`.
    #[inline]
    pub fn cross(self, o: Vec2) -> f32 {
        self.x * o.y - self.y * o.x
    }

    #[inline]
    pub fn length_sq(self) -> f32 {
        self.dot(self)
    }

    /// `hypotf` rather than `sqrtf(dot)` so huge or tiny components do not
    /// overflow or underflow in the intermediate square.
    #[inline]
    pub fn length(self) -> f32 {
        libm::hypotf(self.x, self.y)
    }

    /// Unit vector in the same direction; the zero vector stays zero so callers
    /// facing coincident points get a well-defined (if arbitrary) answer.
    #[inline]
    pub fn normalized(self) -> Vec2 {
        let len = self.length();
        if len > 0.0 { self / len } else { Vec2::ZERO }
    }

    /// Angle CCW from +x, in `[-PI, PI]`.
    #[inline]
    pub fn angle(self) -> f32 {
        libm::atan2f(self.y, self.x)
    }

    /// Rotated 90 degrees CCW. Also `omega x r` for a scalar angular velocity of 1.
    #[inline]
    pub fn perp(self) -> Vec2 {
        Vec2::new(-self.y, self.x)
    }

    /// Rotated CCW by `theta` radians.
    #[inline]
    pub fn rotated(self, theta: f32) -> Vec2 {
        rot(theta, self)
    }
}

impl Add for Vec2 {
    type Output = Vec2;
    #[inline]
    fn add(self, o: Vec2) -> Vec2 {
        Vec2::new(self.x + o.x, self.y + o.y)
    }
}

impl Sub for Vec2 {
    type Output = Vec2;
    #[inline]
    fn sub(self, o: Vec2) -> Vec2 {
        Vec2::new(self.x - o.x, self.y - o.y)
    }
}

impl Neg for Vec2 {
    type Output = Vec2;
    #[inline]
    fn neg(self) -> Vec2 {
        Vec2::new(-self.x, -self.y)
    }
}

impl Mul<f32> for Vec2 {
    type Output = Vec2;
    #[inline]
    fn mul(self, s: f32) -> Vec2 {
        Vec2::new(self.x * s, self.y * s)
    }
}

impl Mul<Vec2> for f32 {
    type Output = Vec2;
    #[inline]
    fn mul(self, v: Vec2) -> Vec2 {
        v * self
    }
}

impl Div<f32> for Vec2 {
    type Output = Vec2;
    #[inline]
    fn div(self, s: f32) -> Vec2 {
        Vec2::new(self.x / s, self.y / s)
    }
}

impl AddAssign for Vec2 {
    #[inline]
    fn add_assign(&mut self, o: Vec2) {
        *self = *self + o;
    }
}

impl SubAssign for Vec2 {
    #[inline]
    fn sub_assign(&mut self, o: Vec2) {
        *self = *self - o;
    }
}

impl MulAssign<f32> for Vec2 {
    #[inline]
    fn mul_assign(&mut self, s: f32) {
        *self = *self * s;
    }
}

/// Rotate `v` CCW by `theta`: `R(theta) * v`. Body-to-world is `rot(heading, p) + pos`.
#[inline]
pub fn rot(theta: f32, v: Vec2) -> Vec2 {
    let (s, c) = (libm::sinf(theta), libm::cosf(theta));
    Vec2::new(c * v.x - s * v.y, s * v.x + c * v.y)
}

/// z component of `a x b`.
#[inline]
pub fn cross(a: Vec2, b: Vec2) -> f32 {
    a.cross(b)
}

/// Wrap an angle into `[-PI, PI]`.
///
/// Angles already inside `[-PI, PI)` come back bit-identical (the floor term is
/// exactly zero), which keeps headings stable when nothing turns.
#[inline]
pub fn wrap_angle(a: f32) -> f32 {
    a - TAU * libm::floorf((a + PI) / TAU)
}

/// Clamp `x` to `[lo, hi]`. Unlike `f32::clamp` this never panics (if `lo > hi`
/// the result is `hi`) and maps NaN to `lo`, so a bad input cannot poison the
/// state with NaN through a clamp.
#[inline]
pub fn clamp(x: f32, lo: f32, hi: f32) -> f32 {
    let x = if x >= lo { x } else { lo };
    if x <= hi { x } else { hi }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn close(a: f32, b: f32) -> bool {
        (a - b).abs() <= 1e-5
    }

    fn close_v(a: Vec2, b: Vec2) -> bool {
        close(a.x, b.x) && close(a.y, b.y)
    }

    #[test]
    fn wrap_angle_maps_into_range() {
        for &(a, want) in &[
            (0.0, 0.0),
            (1.5 * PI, -0.5 * PI),
            (-1.5 * PI, 0.5 * PI),
            (2.0 * PI, 0.0),
            (-2.0 * PI, 0.0),
            (5.0 * PI + 0.25, -PI + 0.25),
            (100.0, 100.0 - 16.0 * TAU),
        ] {
            let w = wrap_angle(a);
            assert!(close(w, want), "wrap_angle({a}) = {w}, want {want}");
            assert!((-PI..=PI).contains(&w));
        }
    }

    #[test]
    fn wrap_angle_is_identity_inside_range() {
        for &a in &[-PI, -3.0, -1.0, -1e-7, 0.0, 1e-7, 1.0, 3.0, PI - 1e-6] {
            assert_eq!(wrap_angle(a).to_bits(), a.to_bits());
        }
    }

    #[test]
    fn wrap_angle_of_pi_stays_on_boundary() {
        let w = wrap_angle(PI);
        assert!(close(w.abs(), PI));
    }

    #[test]
    fn rot_quarter_turns() {
        assert!(close_v(rot(0.5 * PI, Vec2::X), Vec2::Y));
        assert!(close_v(rot(PI, Vec2::X), -Vec2::X));
        assert!(close_v(rot(-0.5 * PI, Vec2::X), -Vec2::Y));
        assert!(close_v(rot(0.5 * PI, Vec2::Y), -Vec2::X));
    }

    #[test]
    fn rot_preserves_length_and_composes() {
        let v = Vec2::new(3.0, -4.0);
        let r = rot(0.7, v);
        assert!(close(r.length(), 5.0));
        assert!(close_v(rot(-0.7, r), v));
        assert!(close_v(rot(0.3, rot(0.4, v)), rot(0.7, v)));
        assert_eq!(v.rotated(0.7), r);
    }

    #[test]
    fn rot_zero_is_exact() {
        let v = Vec2::new(1.25, -7.5);
        assert_eq!(rot(0.0, v), v);
    }

    #[test]
    fn cross_sign_is_ccw_positive() {
        assert_eq!(cross(Vec2::X, Vec2::Y), 1.0);
        assert_eq!(cross(Vec2::Y, Vec2::X), -1.0);
        assert_eq!(cross(Vec2::new(2.0, 0.0), Vec2::new(4.0, 0.0)), 0.0);
        // Torque convention: a thruster at the nose pushing +y spins the ship CCW.
        assert!(cross(Vec2::new(2.0, 0.0), Vec2::new(0.0, 1.0)) > 0.0);
    }

    #[test]
    fn clamp_bounds_and_nan() {
        assert_eq!(clamp(0.5, 0.0, 1.0), 0.5);
        assert_eq!(clamp(-2.0, -1.0, 1.0), -1.0);
        assert_eq!(clamp(2.0, -1.0, 1.0), 1.0);
        assert_eq!(clamp(f32::NAN, -1.0, 1.0), -1.0);
        assert_eq!(clamp(0.0, 1.0, -1.0), -1.0);
    }

    #[test]
    fn vec2_basics() {
        let a = Vec2::new(3.0, 4.0);
        assert_eq!(a.length(), 5.0);
        assert_eq!(a.length_sq(), 25.0);
        assert!(close_v(a.normalized(), Vec2::new(0.6, 0.8)));
        assert_eq!(Vec2::ZERO.normalized(), Vec2::ZERO);
        assert_eq!(a.dot(Vec2::new(-4.0, 3.0)), 0.0);
        assert_eq!(a.perp(), Vec2::new(-4.0, 3.0));
        assert!(close(Vec2::new(0.0, 2.0).angle(), 0.5 * PI));
        assert!(close_v(Vec2::from_angle(0.5 * PI), Vec2::Y));
        assert_eq!(a + a, 2.0 * a);
        assert_eq!(a - a, Vec2::ZERO);
        assert_eq!(a / 2.0, Vec2::new(1.5, 2.0));
        let mut b = a;
        b += a;
        b -= Vec2::X;
        b *= 0.5;
        assert_eq!(b, Vec2::new(2.5, 4.0));
    }
}
