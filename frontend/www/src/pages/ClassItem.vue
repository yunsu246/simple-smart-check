<template>
    <v-ons-list>
        <v-ons-list-item v-for="(item, key) in list" :key="key"
            modifier="chevron"
            @click="transition(item)"
        >
            {{ item.curriculumName +' ('+ item.startDate +'~'+ item.endDate +')' }}
        </v-ons-list-item>
    </v-ons-list>
</template>

<script>
import ClassItemPage from './ClassItemPage.vue';

export default {
  data() {
    return {};
  },
  props: {
    list: Array
  },
  methods: {
    transition(name) {
      this.$store.commit('navigator/options', {
        // Sets animations
        item: name,
        // Resets default options
        callback: () => this.$store.commit('navigator/options', {})
      });
      this.$store.commit('navigator/push', {
        extends: ClassItemPage,
        data() {
          return {
            item: name,
            phoneNo: undefined,
            attendanceTypes: ['In', 'Out'],
            selectAttendanceType: undefined
          }
        }
      });
    }
  }
};
</script>