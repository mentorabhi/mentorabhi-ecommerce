package com.supersports.orderhistory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication public class OrderHistoryApplication {
 public static void main(String[] args){
  var context=SpringApplication.run(OrderHistoryApplication.class,args);
  if(context.getEnvironment().getProperty("order-history.operator-mode",Boolean.class,false)){
   int exitCode=context.getBean(OperatorRunner.class).exitCode();context.close();if(exitCode!=0)System.exit(exitCode);
  }
 }
}
