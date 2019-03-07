/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jclouds.openstack.nova.v2_0;

import static org.jclouds.Constants.PROPERTY_SESSION_INTERVAL;
import static org.jclouds.compute.config.ComputeServiceProperties.TEMPLATE;
import static org.jclouds.openstack.keystone.config.KeystoneProperties.CREDENTIAL_TYPE;
import static org.jclouds.openstack.keystone.config.KeystoneProperties.KEYSTONE_VERSION;
import static org.jclouds.openstack.keystone.config.KeystoneProperties.SERVICE_TYPE;
import static org.jclouds.openstack.nova.v2_0.config.NovaProperties.AUTO_ALLOCATE_FLOATING_IPS;
import static org.jclouds.openstack.nova.v2_0.config.NovaProperties.AUTO_GENERATE_KEYPAIRS;
import static org.jclouds.openstack.nova.v2_0.config.NovaProperties.TIMEOUT_SECURITYGROUP_PRESENT;
import static org.jclouds.reflect.Reflection2.typeToken;

import java.net.URI;
import java.util.Properties;

import org.jclouds.apis.ApiMetadata;
import org.jclouds.compute.ComputeServiceContext;
import org.jclouds.openstack.keystone.auth.config.AuthenticationModule;
import org.jclouds.openstack.keystone.auth.config.CredentialTypes;
import org.jclouds.openstack.keystone.catalog.config.ServiceCatalogModule;
import org.jclouds.openstack.keystone.catalog.config.ServiceCatalogModule.RegionModule;
import org.jclouds.openstack.nova.v2_0.compute.config.NovaComputeServiceContextModule;
import org.jclouds.openstack.nova.v2_0.config.NovaHttpApiModule;
import org.jclouds.openstack.nova.v2_0.config.NovaParserModule;
import org.jclouds.openstack.v2_0.ServiceType;
import org.jclouds.rest.internal.BaseHttpApiMetadata;

import com.google.auto.service.AutoService;
import com.google.common.collect.ImmutableSet;
import com.google.inject.Module;

/**
 * Implementation of {@link ApiMetadata} for Nova 2.0 API
 */
@AutoService(ApiMetadata.class)
public class NovaApiMetadata extends BaseHttpApiMetadata<NovaApi>  {

   @Override
   public Builder toBuilder() {
      return new Builder().fromApiMetadata(this);
   }

   public NovaApiMetadata() {
      this(new Builder());
   }

   protected NovaApiMetadata(Builder builder) {
      super(builder);
   }

   public static Properties defaultProperties() {
      Properties properties = BaseHttpApiMetadata.defaultProperties();
      // auth fail can happen while cloud-init applies keypair updates
      properties.setProperty("jclouds.ssh.max-retries", "7");
      properties.setProperty("jclouds.ssh.retry-auth", "true");
      properties.setProperty(SERVICE_TYPE, ServiceType.COMPUTE);
      properties.setProperty(CREDENTIAL_TYPE, CredentialTypes.PASSWORD_CREDENTIALS);
      properties.setProperty(KEYSTONE_VERSION, "2");
      properties.setProperty(AUTO_ALLOCATE_FLOATING_IPS, "false");
      properties.setProperty(AUTO_GENERATE_KEYPAIRS, "false");
      properties.setProperty(TIMEOUT_SECURITYGROUP_PRESENT, "500");
      // Keystone 1.1 expires tokens after 24 hours and allows renewal 1 hour
      // before expiry by default.  We choose a value less than the latter
      // since the former persists between jclouds invocations.
      properties.setProperty(PROPERTY_SESSION_INTERVAL, 30 * 60 + "");
      properties.put(TEMPLATE, "osFamily=UBUNTU,os64Bit=true,osVersionMatches=16.*");
      return properties;
   }

   public static class Builder extends BaseHttpApiMetadata.Builder<NovaApi, Builder> {

      protected Builder() {
          id("openstack-nova")
         .name("OpenStack Nova Diablo+ API")
         .identityName("${tenantName}:${userName} or ${userName}, if your keystone supports a default tenant")
         .credentialName("${password}")
         .endpointName("Keystone base url ending in /v2.0/")
         .documentation(URI.create("http://api.openstack.org/"))
         .version("2")
         .defaultEndpoint("http://localhost:5000/v2.0/")
         .defaultProperties(NovaApiMetadata.defaultProperties())
         .view(typeToken(ComputeServiceContext.class))
         .defaultModules(ImmutableSet.<Class<? extends Module>>builder()
                                     .add(AuthenticationModule.class)
                                     .add(ServiceCatalogModule.class)
                                     .add(RegionModule.class)
                                     .add(NovaParserModule.class)
                                     .add(NovaHttpApiModule.class)
                                     .add(NovaComputeServiceContextModule.class).build());
      }

      @Override
      public NovaApiMetadata build() {
         return new NovaApiMetadata(this);
      }

      @Override
      protected Builder self() {
         return this;
      }
   }
}
