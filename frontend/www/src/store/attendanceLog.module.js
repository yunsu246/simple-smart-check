import { attendanceLogService } from '../services';

export const attendanceLog = {
    namespaced: true,
    state: {
        checkInOut: {}
    },
    actions: {
        checkInOut({ commit }, { phoneNo, curriculumNo, checkInOut, signature }) {
            commit('postCheckInOutRequest');
            return new Promise((resolve, reject) => {
                attendanceLogService.checkInOut(phoneNo, curriculumNo, checkInOut, signature)
                    .then(
                        response => {
                            commit('postCheckInOutSuccess', response.data);
                            resolve(response);
                        }
                    )
                    .catch(
                        error => {
                            commit('postCheckInOutFailure', error.response.data);
                            reject(error);
                        }
                    );
            })  
        }
    },
    mutations: {
        postCheckInOutRequest(state) {
            state.checkInOut = { loading: true };
        },
        postCheckInOutSuccess(state, attendanceLog) {
            state.checkInOut = { items: attendanceLog };
        },
        postCheckInOutFailure(state, error) {
            state.checkInOut = { error };
        }
    }
}