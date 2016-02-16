module.exports = function(grunt) {

  grunt.loadNpmTasks('grunt-contrib-connect'); 
 
  grunt.initConfig({
    connect: {
      v095: {
        options: {
          open: true,
          hostname: '0.0.0.0',
          port: 9000,
          useAvailablePort: true,
          base: '0.95/original_prototypes'
        }
      },
      v100: {
        options: {
          open: true,
          hostname: '0.0.0.0',
          port: 9001,
          useAvailablePort: true,
          base: '1.0/original_prototypes'
        }
      }
    }
  });

};
