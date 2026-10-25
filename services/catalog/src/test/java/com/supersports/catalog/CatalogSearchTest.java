package com.supersports.catalog;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class CatalogSearchTest {
    @Test void recognizesStandaloneEquipmentAndPluralWithBrandAndSportInEitherOrder() {
        for(String query:new String[]{"SG cricket bats","Cricket SG bat","show me a SG cricket bat"}) {
            var search=CatalogSearch.parse(query);
            assertThat(search.equipment()).isEqualTo("bat");
            assertThat(search.terms()).contains("sg","cricket").doesNotContain("bats");
            assertThat(search.noMatch()).isFalse();
        }
        assertThat(CatalogSearch.parse("balls").equipment()).isEqualTo("ball");
        assertThat(CatalogSearch.parse("pad").equipment()).isEqualTo("pads");
        assertThat(CatalogSearch.parse("jerseys").equipment()).isEqualTo("jersey");
    }
    @Test void doesNotConfuseBattingOrFootballWithEquipmentOrGuessAmbiguousIntent() {
        assertThat(CatalogSearch.parse("football").equipment()).isNull();
        assertThat(CatalogSearch.parse("batting").equipment()).isNull();
        assertThat(CatalogSearch.parse("bat bag").equipment()).isNull();
        assertThat(CatalogSearch.parse("batting gloves").terms()).isEqualTo("batting");
    }
    @Test void handlesCaseWhitespacePunctuationAndEmptyInputWithoutWildcardExpansion() {
        assertThat(CatalogSearch.parse("  BALLS  ").equipment()).isEqualTo("ball");
        assertThat(CatalogSearch.parse("%_!'&").noMatch()).isTrue();
        assertThat(CatalogSearch.parse("show me a").noMatch()).isTrue();
        assertThat(CatalogSearch.parse("DSC Bull 31 pads").terms()).isEqualTo("dsc bull 31");
        assertThat(CatalogSearch.parse("SG & 10%").terms()).isEqualTo("sg 10");
        assertThat(CatalogSearch.parse("%25").literal()).isEqualTo("%25");
        assertThat(CatalogSearch.parse("SG_10").literal()).isEqualTo("SG_10");
    }
}
