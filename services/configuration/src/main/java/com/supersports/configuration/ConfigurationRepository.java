package com.supersports.configuration;

import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Repository
class ConfigurationRepository {
    private final JdbcTemplate jdbc;

    ConfigurationRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public ConfigurationSnapshot read() {
        long revision = jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service = 'configuration'", Long.class);
        var categories = jdbc.query("SELECT id, label FROM configuration_category ORDER BY id",
                (row, index) -> new ConfigurationSnapshot.Category(row.getString("id"), row.getString("label")));
        var settings = jdbc.query("SELECT key, category, value, value_type, activation_mode, revision FROM configuration_setting ORDER BY key",
                (row, index) -> new ConfigurationSnapshot.Setting(row.getString("key"), row.getString("category"),
                        row.getString("value"), ConfigurationSnapshot.ValueType.valueOf(row.getString("value_type")),
                        ConfigurationSnapshot.ActivationMode.valueOf(row.getString("activation_mode")), row.getLong("revision")));
        return new ConfigurationSnapshot(revision, categories, settings);
    }

    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public CheckoutSettings checkoutSettings(){
        long revision=jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service='configuration'",Long.class);
        var rows=jdbc.query("SELECT key,value FROM configuration_setting WHERE key LIKE 'checkout.%' ORDER BY key",(rs,n)->Map.entry(rs.getString("key"),rs.getString("value")));
        var values=new java.util.HashMap<String,String>();rows.forEach(e->values.put(e.getKey(),e.getValue()));
        try{return new CheckoutSettings(revision,Integer.parseInt(values.get("checkout.tax.rate-bps")),Long.parseLong(values.get("checkout.shipping.INR")),Long.parseLong(values.get("checkout.shipping.USD")),Integer.parseInt(values.get("checkout.inventory.reservation-seconds")),values.get("checkout.payment.authorization-mode"));}
        catch(RuntimeException e){throw new IllegalStateException("Checkout simulation settings are incomplete or invalid",e);}
    }
    @Transactional
    SettingUpdate updateCheckoutSetting(String key,String value,long expectedRevision,String actor){
        String storageKey="checkout."+key;var rows=jdbc.queryForList("SELECT value,revision,activation_mode FROM configuration_setting WHERE key=? FOR UPDATE",storageKey);
        if(rows.isEmpty()||!"OPERATOR_EDITABLE".equals(rows.getFirst().get("activation_mode")))throw new IllegalArgumentException("Setting is not editable");
        var row=rows.getFirst();long current=((Number)row.get("revision")).longValue();if(current!=expectedRevision)throw new StaleConfigurationException();
        String next=CheckoutSettingRules.normalize(key,value),old=row.get("value").toString();long revision=current+1;
        jdbc.update("UPDATE configuration_setting SET value=?,revision=? WHERE key=?",next,revision,storageKey);
        jdbc.update("INSERT INTO configuration_setting_audit(setting_key,old_value,new_value,old_revision,new_revision,actor) VALUES (?,?,?,?,?,?)",storageKey,old,next,current,revision,actor);
        jdbc.update("UPDATE bootstrap_metadata SET revision=revision+1 WHERE service='configuration'");
        long global=jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service='configuration'",Long.class);
        return new SettingUpdate(storageKey,next,revision,global);
    }
    @Transactional SettingUpdate updateReturnSetting(String key,String value,long expectedRevision,String actor){
        if(!"window-days".equals(key))throw new IllegalArgumentException("Unknown returns setting");
        String storageKey="returns.window-days";var rows=jdbc.queryForList("SELECT value,revision,activation_mode FROM configuration_setting WHERE key=? FOR UPDATE",storageKey);
        if(rows.isEmpty()||!"OPERATOR_EDITABLE".equals(rows.getFirst().get("activation_mode")))throw new IllegalArgumentException("Setting is not editable");
        var row=rows.getFirst();long current=((Number)row.get("revision")).longValue();if(current!=expectedRevision)throw new StaleConfigurationException();
        String next=CheckoutSettingRules.normalize(storageKey,value);
        String old=row.get("value").toString();long revision=current+1;
        jdbc.update("UPDATE configuration_setting SET value=?,revision=? WHERE key=?",next,revision,storageKey);
        jdbc.update("INSERT INTO configuration_setting_audit(setting_key,old_value,new_value,old_revision,new_revision,actor) VALUES (?,?,?,?,?,?)",storageKey,old,next,current,revision,actor);
        jdbc.update("UPDATE bootstrap_metadata SET revision=revision+1 WHERE service='configuration'");
        long global=jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service='configuration'",Long.class);
        return new SettingUpdate(storageKey,next,revision,global);
    }
    public record SettingUpdate(String key,String value,long settingRevision,long revision){}
    static final class StaleConfigurationException extends RuntimeException{}
    public record CheckoutSettings(long revision,int taxRateBps,long shippingInrMinor,long shippingUsdMinor,int reservationSeconds,String authorizationMode){}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ) ReturnPolicy returnsPolicy(){
        var rows=jdbc.queryForList("SELECT value,revision FROM configuration_setting WHERE key='returns.window-days'");
        if(rows.isEmpty())throw new IllegalStateException("Return policy is not configured");var row=rows.getFirst();
        return new ReturnPolicy(Long.parseLong(row.get("value").toString()),((Number)row.get("revision")).longValue());
    }
    public record ReturnPolicy(long windowDays,long policyRevision){}
}
