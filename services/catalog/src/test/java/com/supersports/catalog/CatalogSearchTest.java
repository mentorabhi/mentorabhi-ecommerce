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
    @Test void specificAccessoryIntentPrecedesTheGenericBatAndPreservesBrandTerms() {
        for(String[] pair:new String[][]{{"SG bat grips","bat-grip"},{"DSC bat oil","bat-oil"},{"bat toe guard","toe-guard"},{"batting tee","batting-tee"},{"bat care kit","bat-care-kit"},{"padded shorts","padded-inners"},{"inner thigh pad","inner-thigh-guard"},{"shin guards","fielding-shin-guards"}}) {
            var query=CatalogSearch.parse(pair[0]);
            assertThat(query.equipment()).isEqualTo(pair[1]);
            assertThat(query.equipmentTypePattern()).contains(pair[1]);
            assertThat(query.terms()).doesNotContain("bat");
        }
        assertThat(CatalogSearch.parse("SG bat grips").terms()).isEqualTo("sg");
        assertThat(CatalogSearch.parse("bat grip bat oil").equipment()).isNull();
        assertThat(CatalogSearch.parse("wicketkeeping gloves").terms()).isEqualTo("wicket keeping");
        assertThat(CatalogSearch.parse("rubber shoes").equipment()).isEqualTo("boots");
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
