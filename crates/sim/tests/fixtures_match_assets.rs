//! The hand-built test catalogue must describe the same hulls and weapons as the
//! shipped YAML; otherwise tests pass against numbers the game does not use.

mod common;

#[test]
fn hand_built_catalogue_matches_shipped_assets() {
    let assets = common::asset_catalogue();
    let fixture = common::test_catalogue();
    assert_eq!(fixture.weapons, assets.weapons);
    assert_eq!(fixture.hulls.len(), assets.hulls.len());
    for (f, a) in fixture.hulls.iter().zip(&assets.hulls) {
        assert_eq!(f, a, "hull {} differs from its YAML", a.name);
    }
}
