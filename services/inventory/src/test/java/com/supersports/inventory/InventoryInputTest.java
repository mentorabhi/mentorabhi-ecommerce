package com.supersports.inventory;
import org.junit.jupiter.api.Test;import static org.assertj.core.api.Assertions.*;
class InventoryInputTest{
 @Test void rejectsZeroMovesAndWeakIdempotencyKeys(){assertThatThrownBy(()->InventoryRules.validateAdjustment(0,"cycle count","key-00001")).isInstanceOf(IllegalArgumentException.class);assertThatThrownBy(()->InventoryRules.validateAdjustment(2," ","key-00001")).isInstanceOf(IllegalArgumentException.class);assertThatThrownBy(()->InventoryRules.validateAdjustment(2,"cycle count","short")).isInstanceOf(IllegalArgumentException.class);}
 @Test void stockCannotGoBelowZeroOrOverflow(){assertThat(InventoryRules.resultingStock(10,-4)).isEqualTo(6);assertThatThrownBy(()->InventoryRules.resultingStock(2,-3)).isInstanceOf(IllegalArgumentException.class);assertThatThrownBy(()->InventoryRules.resultingStock(Long.MAX_VALUE,1)).isInstanceOf(IllegalArgumentException.class);}
}
