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
package org.jclouds.openstack.nova.v2_0.features;

import static org.testng.Assert.assertEquals;

import org.jclouds.http.HttpRequest;
import org.jclouds.http.HttpResponse;
import org.jclouds.openstack.nova.v2_0.NovaApi;
import org.jclouds.openstack.nova.v2_0.internal.BaseNovaApiExpectTest;
import org.jclouds.openstack.nova.v2_0.parse.ParseImageListTest;
import org.jclouds.openstack.nova.v2_0.parse.ParseImageTest;
import org.jclouds.openstack.nova.v2_0.parse.ParseMetadataListTest;
import org.jclouds.openstack.nova.v2_0.parse.ParseMetadataUpdateTest;
import org.jclouds.util.Strings2;
import org.testng.annotations.Test;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;

/**
 * Tests annotation parsing of {@code ImageApi}
 */
@Test(groups = "unit", testName = "ImageApiExpectTest")
public class ImageApiExpectTest extends BaseNovaApiExpectTest {

   public void testListImagesWhenResponseIs2xx() throws Exception {
      HttpRequest list = HttpRequest.builder()
            .method("GET")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .build();

      HttpResponse listResponse = HttpResponse.builder().statusCode(200)
            .payload(payloadFromResource("/image_list.json")).build();

      NovaApi apiWhenImagesExist = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
            responseWithKeystoneAccess, list, listResponse);

      assertEquals(apiWhenImagesExist.getConfiguredRegions(), ImmutableSet.of("az-1.region-a.geo-1", "az-2.region-a.geo-1", "az-3.region-a.geo-1"));

      assertEquals(apiWhenImagesExist.getImageApi("az-1.region-a.geo-1").list().concat().toString(),
            new ParseImageListTest().expected().toString());
   }

   public void testGetImageWhenResponseIs2xx() throws Exception {

      HttpRequest getImage = HttpRequest.builder()
            .method("GET")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/52415800-8b69-11e0-9b19-734f5736d2a2")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .build();

      HttpResponse getImageResponse = HttpResponse.builder().statusCode(200)
            .payload(payloadFromResource("/image_details.json")).build();

      NovaApi apiWhenImagesExist = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
            responseWithKeystoneAccess, getImage, getImageResponse);

      assertEquals(
            apiWhenImagesExist.getImageApi("az-1.region-a.geo-1").get("52415800-8b69-11e0-9b19-734f5736d2a2")
                  .toString(), new ParseImageTest().expected().toString());
   }

   public void testListMetadataWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      HttpRequest getMetadata = HttpRequest.builder()
            .method("GET")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .build();

      HttpResponse getMetadataResponse = HttpResponse.builder().statusCode(200)
              .payload(payloadFromResource("/metadata_list.json")).build();

      NovaApi apiWhenServerExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, getMetadata, getMetadataResponse);

      assertEquals(apiWhenServerExists.getImageApi("az-1.region-a.geo-1").getMetadata(imageId).toString(),
             new ParseMetadataListTest().expected().toString());
   }

   public void testSetMetadataWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      ImmutableMap<String, String> metadata = new ImmutableMap.Builder<String, String>()
              .put("Server Label", "Web Head 1")
              .put("Image Version", "2.1")
              .build();

      HttpRequest setMetadata = HttpRequest.builder()
            .method("PUT")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .payload(payloadFromStringWithContentType(
                  "{\"metadata\":{\"Server Label\":\"Web Head 1\",\"Image Version\":\"2.1\"}}", "application/json"))
            .build();

      HttpResponse setMetadataResponse = HttpResponse.builder().statusCode(200)
              .payload(payloadFromResource("/metadata_list.json")).build();

      NovaApi apiWhenImageExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, setMetadata, setMetadataResponse);

      assertEquals(apiWhenImageExists.getImageApi("az-1.region-a.geo-1").setMetadata(imageId, metadata).toString(),
             new ParseMetadataListTest().expected().toString());
   }

   public void testUpdateMetadataWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      ImmutableMap<String, String> metadata = new ImmutableMap.Builder<String, String>()
              .put("Server Label", "Web Head 2")
              .put("Server Description", "Simple Server")
              .build();

      HttpRequest setMetadata = HttpRequest.builder()
            .method("POST")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .payload(payloadFromStringWithContentType(
                  "{\"metadata\":{\"Server Label\":\"Web Head 2\",\"Server Description\":\"Simple Server\"}}", "application/json"))
            .build();

      HttpResponse setMetadataResponse = HttpResponse.builder().statusCode(200)
              .payload(payloadFromResource("/metadata_updated.json")).build();

      NovaApi apiWhenServerExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, setMetadata, setMetadataResponse);

      assertEquals(apiWhenServerExists.getImageApi("az-1.region-a.geo-1").updateMetadata(imageId, metadata).toString(),
             new ParseMetadataUpdateTest().expected().toString());
   }

   public void testGetMetadataItemWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      String key = "Image Version";

      HttpRequest getMetadata = HttpRequest.builder()
            .method("GET")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata/" +
                  Strings2.urlEncode(key))
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .build();

      HttpResponse getMetadataResponse = HttpResponse.builder().statusCode(200)
              .payload(payloadFromString("{\"metadata\":{\"Image Version\":\"2.5\"}}")).build();

      NovaApi apiWhenServerExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, getMetadata, getMetadataResponse);

      assertEquals(apiWhenServerExists.getImageApi("az-1.region-a.geo-1").getMetadata(imageId, "Image Version").toString(),
             "2.5");
   }

   public void testSetMetadataItemWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      String key = "Image Version";

      HttpRequest updateMetadata = HttpRequest.builder()
            .method("PUT")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata/" + "Image%20Version")
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .payload(payloadFromStringWithContentType("{\"metadata\":{\"Image Version\":\"2.5\"}}", "application/json"))
            .build();

      HttpResponse updateMetadataResponse = HttpResponse.builder().statusCode(200)
              .payload(payloadFromStringWithContentType("{\"metadata\":{\"Image Version\":\"2.5\"}}", "application/json")).build();

      NovaApi apiWhenServerExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, updateMetadata, updateMetadataResponse);

      assertEquals(apiWhenServerExists.getImageApi("az-1.region-a.geo-1").updateMetadata(imageId, key, "2.5").toString(),
             "2.5");
   }

   public void testDeleteMetadataItemWhenResponseIs2xx() throws Exception {
      String imageId = "52415800-8b69-11e0-9b19-734f5736d2a2";
      String key = "Image Version";

      HttpRequest deleteMetadata = HttpRequest.builder()
            .method("DELETE")
            .endpoint("https://az-1.region-a.geo-1.compute.hpcloudsvc.com/v2/3456/images/" + imageId + "/metadata/" +
                  Strings2.urlEncode(key))
            .addHeader("Accept", "application/json")
            .addHeader("X-Auth-Token", authToken)
            .build();

      HttpResponse deleteMetadataResponse = HttpResponse.builder().statusCode(204).build();

      NovaApi apiWhenImageExists = requestsSendResponses(keystoneAuthWithUsernameAndPasswordAndTenantName,
               responseWithKeystoneAccess, deleteMetadata, deleteMetadataResponse);

      apiWhenImageExists.getImageApi("az-1.region-a.geo-1").deleteMetadata(imageId, key);
   }

}
