<template>
  <div class="p-6">
    <InstagramWidget
      apiUrl="https://api-instagram.redbeauty.com.br/api/instagram/posts"
      title="@redbeauty"
      instagramUrl="https://instagram.com/redbeauty"
      :showCaptions="true"
      :showPeek="true"
    />
  </div>
</template>

<script setup lang="ts">
import InstagramWidget from "./components/InstagramWidget.vue";
</script>
